"""Tests for Checkpoint class and domain checkpoint integration."""

from collections.abc import Sequence
from pathlib import Path

from pydantic_ai.mcp import MCPServer
from pydantic_evals.evaluators import Evaluator

from mcp_evals.checkpoint import Checkpoint
from mcp_evals.domain import Domain
from mcp_evals.secrets import DomainSecrets, TaskSecrets
from mcp_evals.task import Task


class TestCheckpointInit:
    """Tests for Checkpoint initialization."""

    def test_stores_path(self, tmp_path: Path) -> None:
        """Checkpoint stores the given path."""
        path = tmp_path / "checkpoint.txt"
        cp = Checkpoint(path)
        assert cp.path == path


class TestCheckpointLoad:
    """Tests for Checkpoint.load()."""

    def test_load_when_file_missing_leaves_finished_keys_empty(self, tmp_path: Path) -> None:
        """When checkpoint file does not exist, load() leaves _finished_keys empty."""
        path = tmp_path / "missing.txt"
        cp = Checkpoint(path)
        cp.load()
        assert cp.is_finished("train", "t1") is False
        assert cp.is_finished("test", "t2") is False

    def test_load_parses_keys_from_file(self, tmp_path: Path) -> None:
        """load() reads scope::task_name keys from file, one per line."""
        path = tmp_path / "ckpt.txt"
        path.write_text("train::task_a\ntest::task_b\ntrain::task_c\n", encoding="utf-8")
        cp = Checkpoint(path)
        cp.load()
        assert cp.is_finished("train", "task_a") is True
        assert cp.is_finished("test", "task_b") is True
        assert cp.is_finished("train", "task_c") is True
        assert cp.is_finished("train", "task_b") is False
        assert cp.is_finished("other", "task_a") is False

    def test_load_ignores_blank_lines(self, tmp_path: Path) -> None:
        """load() ignores empty and whitespace-only lines."""
        path = tmp_path / "ckpt.txt"
        path.write_text("scope::t1\n\n  \nscope::t2\n", encoding="utf-8")
        cp = Checkpoint(path)
        cp.load()
        assert cp.is_finished("scope", "t1") is True
        assert cp.is_finished("scope", "t2") is True

    def test_load_is_idempotent(self, tmp_path: Path) -> None:
        """Multiple load() calls replace state from disk (idempotent)."""
        path = tmp_path / "ckpt.txt"
        path.write_text("s1::t1\n", encoding="utf-8")
        cp = Checkpoint(path)
        cp.load()
        assert cp.is_finished("s1", "t1") is True
        path.write_text("s2::t2\n", encoding="utf-8")
        cp.load()
        assert cp.is_finished("s1", "t1") is False
        assert cp.is_finished("s2", "t2") is True


class TestCheckpointIsFinished:
    """Tests for Checkpoint.is_finished()."""

    def test_returns_false_before_record(self, tmp_path: Path) -> None:
        """is_finished returns False for any scope/task before record_finished."""
        cp = Checkpoint(tmp_path / "ckpt.txt")
        assert cp.is_finished("default", "task1") is False

    def test_returns_true_after_record(self, tmp_path: Path) -> None:
        """is_finished returns True after record_finished for that scope and task."""
        path = tmp_path / "ckpt.txt"
        cp = Checkpoint(path)
        cp.record_finished("train", "my_task")
        assert cp.is_finished("train", "my_task") is True
        assert cp.is_finished("train", "other") is False
        assert cp.is_finished("test", "my_task") is False


class TestCheckpointRecordFinished:
    """Tests for Checkpoint.record_finished()."""

    def test_creates_parent_dirs_and_appends_to_file(self, tmp_path: Path) -> None:
        """record_finished creates parent dirs if needed and appends key to file."""
        path = tmp_path / "subdir" / "ckpt.txt"
        assert not path.parent.exists()
        cp = Checkpoint(path)
        cp.record_finished("scope", "task_name")
        assert path.parent.exists()
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert content.strip() == "scope::task_name"

    def test_multiple_records_append_lines(self, tmp_path: Path) -> None:
        """Multiple record_finished calls append one line each."""
        path = tmp_path / "ckpt.txt"
        cp = Checkpoint(path)
        cp.record_finished("s1", "t1")
        cp.record_finished("s1", "t2")
        cp.record_finished("s2", "t1")
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert lines == ["s1::t1", "s1::t2", "s2::t1"]

    def test_record_is_idempotent(self, tmp_path: Path) -> None:
        """Recording the same scope/task twice does not duplicate in file."""
        path = tmp_path / "ckpt.txt"
        cp = Checkpoint(path)
        cp.record_finished("scope", "task")
        cp.record_finished("scope", "task")
        content = path.read_text(encoding="utf-8")
        assert content.count("scope::task") == 1

    def test_key_format_is_scope_double_colon_task_name(self, tmp_path: Path) -> None:
        """Key format is scope::task_name (double colon)."""
        path = tmp_path / "ckpt.txt"
        cp = Checkpoint(path)
        cp.record_finished("my_scope", "my_task")
        raw = path.read_text(encoding="utf-8").strip()
        assert raw == "my_scope::my_task"


# --- Domain + checkpoint integration ---


class MinimalTask(Task[TaskSecrets, str]):
    """Minimal task for checkpoint filtering tests."""

    goal = "goal"
    output_type = str
    evaluators: tuple[Evaluator["MinimalTask", object], ...] = ()

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


class MinimalDomain(Domain[DomainSecrets]):
    """Minimal domain with configurable tasks and optional checkpoint."""

    name = "minimal"

    def __init__(
        self,
        task_names: list[str],
        *,
        checkpoint_path: Path | str | None = None,
    ) -> None:
        super().__init__(checkpoint_path=checkpoint_path)
        self._task_names = task_names

    def mcp_servers(self) -> Sequence[MCPServer]:
        return []

    def _tasks_impl(self) -> Sequence[Task[TaskSecrets, str]]:
        return [MinimalTask(n) for n in self._task_names]


class TestDomainCheckpointIntegration:
    """Tests for Domain checkpoint_path and tasks() filtering."""

    def test_domain_without_checkpoint_path_has_checkpoint_none(self) -> None:
        """When checkpoint_path is not passed, domain.checkpoint is None."""
        domain = MinimalDomain(["t1", "t2"])
        assert domain.checkpoint is None

    def test_domain_with_checkpoint_path_has_checkpoint_instance(self, tmp_path: Path) -> None:
        """When checkpoint_path is passed, domain.checkpoint is a Checkpoint instance."""
        path = tmp_path / "ckpt.txt"
        domain = MinimalDomain(["t1"], checkpoint_path=path)
        assert domain.checkpoint is not None
        assert domain.checkpoint.path == path

    def test_tasks_with_scope_none_returns_all_unfiltered(self, tmp_path: Path) -> None:
        """tasks(scope=None) returns all tasks regardless of checkpoint."""
        path = tmp_path / "ckpt.txt"
        path.write_text("default::t1\n", encoding="utf-8")
        domain = MinimalDomain(["t1", "t2"], checkpoint_path=path)
        assert domain.checkpoint is not None
        domain.checkpoint.load()
        result = domain.tasks(scope=None)
        names = [t.name for t in result]
        assert names == ["t1", "t2"]

    def test_tasks_with_scope_filters_by_checkpoint(self, tmp_path: Path) -> None:
        """tasks(scope=...) excludes tasks already recorded in checkpoint."""
        path = tmp_path / "ckpt.txt"
        path.write_text("default::t1\n", encoding="utf-8")
        domain = MinimalDomain(["t1", "t2", "t3"], checkpoint_path=path)
        assert domain.checkpoint is not None
        domain.checkpoint.load()
        result = domain.tasks(scope="default")
        names = [t.name for t in result]
        assert names == ["t2", "t3"]

    def test_tasks_with_checkpoint_none_returns_all(self) -> None:
        """When domain has no checkpoint, tasks(scope=...) returns all tasks."""
        domain = MinimalDomain(["t1", "t2"])
        result = domain.tasks(scope="default")
        names = [t.name for t in result]
        assert names == ["t1", "t2"]
