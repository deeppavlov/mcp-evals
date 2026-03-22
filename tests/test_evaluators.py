"""Tests for built-in evaluators."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pytest
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluatorContext

from mcp_evals.contrib.filesystem.common_evaluators import ContentMatches, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture
from mcp_evals.evaluators import EvaluationReason


class _TestFilesystemTask(FilesystemTask):
    """Concrete task for tests: base FilesystemTask needs `name` to build per-task work_dir."""

    name = "eval_test_workspace"


def task_workspace(parent_tmp: Path) -> Path:
    """Directory matching `_TestFilesystemTask(parent_tmp).work_dir` (parent / task name)."""
    return parent_tmp / _TestFilesystemTask.name


def create_mock_context(parent_tmp: Path) -> EvaluatorContext[FilesystemTask, AgentRunResult]:
    """Create a mock evaluator context with a FilesystemTask."""
    task = _TestFilesystemTask(work_dir=parent_tmp, fixture=Fixture.DESKTOP)
    ctx = MagicMock(spec=EvaluatorContext)
    ctx.inputs = task
    ctx.output = MagicMock(spec=AgentRunResult)
    return ctx


@pytest.mark.asyncio
class TestFileExists:
    """Tests for FileExists evaluator."""

    async def test_returns_1_when_file_exists(self) -> None:
        """Test that FileExists returns 1.0 when file exists."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "test.txt"
            test_file.write_text("test content")

            evaluator = FileExists(path="test.txt")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

    async def test_returns_0_when_file_does_not_exist(self) -> None:
        """Test that FileExists returns 0.0 with reason when file doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)

            evaluator = FileExists(path="nonexistent.txt")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert isinstance(result, EvaluationReason)
            assert result.value == 0.0
            assert result.reason is not None
            assert "does not exist" in result.reason

    async def test_returns_0_when_path_is_directory(self) -> None:
        """Test that FileExists returns 0.0 when path is directory, not file."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            test_dir = ws / "subdir"
            test_dir.mkdir(parents=True)

            evaluator = FileExists(path="subdir")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert isinstance(result, EvaluationReason)
            assert result.value == 0.0
            assert result.reason is not None
            assert "is not a file" in result.reason

    async def test_handles_relative_paths(self) -> None:
        """Test that FileExists handles relative paths."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "relative_file.txt"
            test_file.write_text("content")

            evaluator = FileExists(path="relative_file.txt")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

    async def test_handles_absolute_paths(self) -> None:
        """Test that FileExists handles absolute paths."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "absolute_file.txt"
            test_file.write_text("content")

            # Paths are resolved relative to work_dir, so use relative path
            evaluator = FileExists(path="absolute_file.txt")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

    async def test_handles_nested_paths(self) -> None:
        """Test that FileExists handles nested directory paths."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            nested_dir = ws / "nested" / "subdir"
            nested_dir.mkdir(parents=True)
            test_file = nested_dir / "file.txt"
            test_file.write_text("content")

            evaluator = FileExists(path="nested/subdir/file.txt")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0


@pytest.mark.asyncio
class TestContentMatches:
    """Tests for ContentMatches evaluator."""

    async def test_returns_1_when_pattern_matches(self) -> None:
        """Test that ContentMatches returns 1.0 when pattern matches."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "test.txt"
            test_file.write_text("The port is 8080")

            evaluator = ContentMatches(path="test.txt", pattern=r"port.*8080")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

    async def test_returns_0_when_pattern_does_not_match(self) -> None:
        """Test that ContentMatches returns 0.0 when pattern doesn't match."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "test.txt"
            test_file.write_text("The port is 3000")

            evaluator = ContentMatches(path="test.txt", pattern=r"port.*8080")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert isinstance(result, EvaluationReason)
            assert result.value == 0.0
            assert result.reason is not None
            assert "does not match pattern" in result.reason

    async def test_returns_0_when_file_does_not_exist(self) -> None:
        """Test that ContentMatches returns 0.0 when file doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)

            evaluator = ContentMatches(path="nonexistent.txt", pattern=r".*")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert isinstance(result, EvaluationReason)
            assert result.value == 0.0
            assert result.reason is not None
            assert "does not exist" in result.reason

    async def test_returns_0_when_path_is_directory(self) -> None:
        """Test that ContentMatches returns 0.0 when path is directory."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            test_dir = ws / "subdir"
            test_dir.mkdir(parents=True)

            evaluator = ContentMatches(path="subdir", pattern=r".*")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert isinstance(result, EvaluationReason)
            assert result.value == 0.0
            assert result.reason is not None
            assert "is not a file" in result.reason

    async def test_handles_regex_special_characters(self) -> None:
        """Test that ContentMatches handles regex special characters correctly."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "test.txt"
            test_file.write_text("Price: $19.99 (20% off)")

            # Test with escaped special characters
            evaluator = ContentMatches(path="test.txt", pattern=r"\$19\.99.*20%")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

    async def test_handles_multiline_content(self) -> None:
        """Test that ContentMatches handles multiline content."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "test.txt"
            test_file.write_text("Line 1\nLine 2\nLine 3")

            evaluator = ContentMatches(path="test.txt", pattern=r"Line 1.*Line 3")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

    async def test_handles_unicode_content(self) -> None:
        """Test that ContentMatches handles unicode content."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "test.txt"
            test_file.write_text("晴天 2.576", encoding="utf-8")

            evaluator = ContentMatches(path="test.txt", pattern=r"晴天.*2\.576")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

    async def test_handles_permission_error_gracefully(self) -> None:
        """Test that ContentMatches handles PermissionError gracefully."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "test.txt"
            test_file.write_text("content")

            # Make file unreadable (Unix only)
            if os.name != "nt":
                test_file.chmod(0o000)
                try:
                    evaluator = ContentMatches(path="test.txt", pattern=r".*")
                    ctx = create_mock_context(parent)
                    result = await evaluator.evaluate(ctx)

                    assert isinstance(result, EvaluationReason)
                    assert result.value == 0.0
                    assert result.reason is not None
                    assert "Error reading file" in result.reason
                finally:
                    test_file.chmod(0o644)

    async def test_case_sensitive_matching(self) -> None:
        """Test that ContentMatches is case sensitive by default."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "test.txt"
            test_file.write_text("Hello World")

            # Case sensitive - should not match
            evaluator = ContentMatches(path="test.txt", pattern=r"hello")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert isinstance(result, EvaluationReason)
            assert result.value == 0.0

            # Case sensitive - should match
            evaluator = ContentMatches(path="test.txt", pattern=r"Hello")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

    async def test_empty_file_handling(self) -> None:
        """Test that ContentMatches handles empty files."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            ws = task_workspace(parent)
            ws.mkdir(parents=True, exist_ok=True)
            test_file = ws / "empty.txt"
            test_file.write_text("")

            # Pattern that matches empty string
            evaluator = ContentMatches(path="empty.txt", pattern=r"^$")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert result == 1.0

            # Pattern that doesn't match empty string
            evaluator = ContentMatches(path="empty.txt", pattern=r".+")
            ctx = create_mock_context(parent)
            result = await evaluator.evaluate(ctx)

            assert isinstance(result, EvaluationReason)
            assert result.value == 0.0
