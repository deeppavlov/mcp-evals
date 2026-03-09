"""Tests for RunState and run state persistence."""

from pathlib import Path

import pytest
from anyio import Path as AnyioPath

from mcp_evals._internal.runner._groupers import PlainGrouper
from mcp_evals._internal.runner._run_state import (
    RunState,
    RunStateHeader,
    SplitPhaseStartedEvent,
    TaskFinishedEvent,
    run_state_path,
)
from mcp_evals._internal.runner._splits import Splitting


def _splittings_plain(n_tasks: int) -> list[Splitting]:
    """Plain grouper: one split, no train, all test."""
    return list(PlainGrouper().splittings(n_tasks))


@pytest.mark.asyncio
class TestRunStateLoad:
    """Tests for RunState.load()."""

    async def test_load_when_file_missing_returns_empty_state(self, tmp_path: Path) -> None:
        """When state file does not exist, load returns state with n_tasks and fingerprint set."""
        path = AnyioPath(tmp_path / "missing.jsonl")
        n_tasks = 5
        splittings = _splittings_plain(n_tasks)

        state = await RunState.load(path, n_tasks=n_tasks, splittings=splittings)

        assert state._n_tasks == n_tasks
        assert state._fingerprint == [[0, 5]]
        assert not state.has_split_phase_started(0, "train")
        assert not state.has_split_phase_started(0, "test")
        task_names = [f"task_{i}" for i in range(n_tasks)]
        assert state.pending_indices(0, "test", list(range(n_tasks)), task_names) == list(range(n_tasks))

    async def test_load_with_valid_jsonl_restores_state(self, tmp_path: Path) -> None:
        """When state file has valid header and events, load restores phase and task state."""
        path = AnyioPath(tmp_path / "state.jsonl")
        n_tasks = 4
        splittings = _splittings_plain(n_tasks)
        header = RunStateHeader(n_tasks=n_tasks, splitting_fingerprint=[[0, 4]])
        lines = [
            header.model_dump_json(),
            SplitPhaseStartedEvent(split_idx=0, phase="test").model_dump_json(),
            TaskFinishedEvent(split_idx=0, phase="test", task_name="task_0").model_dump_json(),
            TaskFinishedEvent(split_idx=0, phase="test", task_name="task_2").model_dump_json(),
        ]
        await path.parent.mkdir(parents=True, exist_ok=True)
        async with await path.open("w") as f:
            await f.write("\n".join(lines) + "\n")

        state = await RunState.load(path, n_tasks=n_tasks, splittings=splittings)

        assert state._n_tasks == n_tasks
        assert state.has_split_phase_started(0, "test")
        task_names = [f"task_{i}" for i in range(n_tasks)]
        pending = state.pending_indices(0, "test", list(range(n_tasks)), task_names)
        assert pending == [1, 3]

    async def test_load_fingerprint_mismatch_raises(self, tmp_path: Path) -> None:
        """When stored fingerprint does not match current splittings, load raises ValueError."""
        path = AnyioPath(tmp_path / "state.jsonl")
        header = RunStateHeader(n_tasks=5, splitting_fingerprint=[[2, 3]])
        await path.parent.mkdir(parents=True, exist_ok=True)
        async with await path.open("w") as f:
            await f.write(header.model_dump_json() + "\n")

        n_tasks = 5
        splittings = _splittings_plain(n_tasks)

        with pytest.raises(ValueError, match="Cannot resume"):
            await RunState.load(path, n_tasks=n_tasks, splittings=splittings)

    async def test_load_n_tasks_mismatch_raises(self, tmp_path: Path) -> None:
        """When stored n_tasks differs from current, load raises ValueError."""
        path = AnyioPath(tmp_path / "state.jsonl")
        header = RunStateHeader(n_tasks=10, splitting_fingerprint=[[0, 5]])
        await path.parent.mkdir(parents=True, exist_ok=True)
        async with await path.open("w") as f:
            await f.write(header.model_dump_json() + "\n")

        n_tasks = 5
        splittings = _splittings_plain(n_tasks)

        with pytest.raises(ValueError, match="Cannot resume"):
            await RunState.load(path, n_tasks=n_tasks, splittings=splittings)


@pytest.mark.asyncio
class TestRunStateQueries:
    """Tests for has_split_phase_started and pending_indices."""

    async def test_has_split_phase_started_false_by_default(self, tmp_path: Path) -> None:
        """New state has no phase started."""
        path = AnyioPath(tmp_path / "state.jsonl")
        state = await RunState.load(path, n_tasks=3, splittings=_splittings_plain(3))
        assert not state.has_split_phase_started(0, "train")
        assert not state.has_split_phase_started(0, "test")

    async def test_pending_indices_returns_all_when_none_finished(self, tmp_path: Path) -> None:
        """pending_indices returns all given indices when no tasks are marked finished."""
        path = AnyioPath(tmp_path / "state.jsonl")
        state = await RunState.load(path, n_tasks=4, splittings=_splittings_plain(4))
        task_names = [f"t{i}" for i in range(4)]
        indices = [0, 2, 3]
        assert state.pending_indices(0, "test", indices, task_names) == [0, 2, 3]


@pytest.mark.asyncio
class TestRunStateMarkAndPersist:
    """Tests for mark_* methods and file persistence."""

    async def test_mark_split_phase_started_writes_and_updates_state(self, tmp_path: Path) -> None:
        """mark_split_phase_started appends event to file and sets has_split_phase_started."""
        path = AnyioPath(tmp_path / "state.jsonl")
        state = await RunState.load(path, n_tasks=2, splittings=_splittings_plain(2))
        assert not state.has_split_phase_started(0, "train")

        await state.mark_split_phase_started(0, "train")

        assert state.has_split_phase_started(0, "train")
        content = await path.read_text()
        lines = content.strip().splitlines()
        assert len(lines) >= 2
        assert '"split_phase_started"' in lines[1] or "split_phase_started" in lines[1]

    async def test_mark_task_finished_writes_and_pending_excludes_it(self, tmp_path: Path) -> None:
        """mark_task_finished appends event and pending_indices no longer includes that task."""
        path = AnyioPath(tmp_path / "state.jsonl")
        state = await RunState.load(path, n_tasks=3, splittings=_splittings_plain(3))
        task_names = ["a", "b", "c"]

        await state.mark_split_phase_started(0, "test")
        await state.mark_task_finished(0, "test", "b")

        pending = state.pending_indices(0, "test", [0, 1, 2], task_names)
        assert pending == [0, 2]

    async def test_mark_split_finished_writes_event(self, tmp_path: Path) -> None:
        """mark_split_finished appends split_finished event to file."""
        path = AnyioPath(tmp_path / "state.jsonl")
        state = await RunState.load(path, n_tasks=2, splittings=_splittings_plain(2))

        await state.mark_split_phase_started(0, "test")
        await state.mark_split_finished(0)

        content = await path.read_text()
        assert "split_finished" in content


@pytest.mark.asyncio
class TestRunStateClear:
    """Tests for RunState.clear()."""

    async def test_clear_removes_state_file(self, tmp_path: Path) -> None:
        """clear() removes the state file if it exists."""
        path = AnyioPath(tmp_path / "state.jsonl")
        state = await RunState.load(path, n_tasks=2, splittings=_splittings_plain(2))
        await state.mark_split_phase_started(0, "test")

        assert await path.exists()

        await state.clear()

        assert not await path.exists()

    async def test_clear_when_file_missing_does_not_raise(self, tmp_path: Path) -> None:
        """clear() when file does not exist does not raise."""
        path = AnyioPath(tmp_path / "nonexistent.jsonl")
        state = RunState(path)

        await state.clear()


@pytest.mark.asyncio
class TestRunStatePath:
    """Tests for run_state_path()."""

    async def test_run_state_path_uses_state_dir_and_experiment_name(self, tmp_path: Path) -> None:
        """run_state_path returns path under state_dir with experiment name and .jsonl."""
        path = await run_state_path("my-exp", state_dir=tmp_path)
        path_str = str(path)
        assert "my-exp" in path_str
        assert path_str.endswith(".jsonl")
        assert ".mcp_evals_state" in path_str
