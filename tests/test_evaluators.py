"""Tests for built-in evaluators."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pytest

from mcp_evals.evaluators import ContentMatches, FileExists


@pytest.mark.asyncio
class TestFileExists:
    """Tests for FileExists evaluator."""

    async def test_returns_1_when_file_exists(self) -> None:
        """Test that FileExists returns 1.0 when file exists."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            evaluator = FileExists(path=str(test_file))
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0

    async def test_returns_0_when_file_does_not_exist(self) -> None:
        """Test that FileExists returns 0.0 with reason when file doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "nonexistent.txt"

            evaluator = FileExists(path=str(test_file))
            result = await evaluator.evaluate(MagicMock())

            assert result.value == 0.0
            assert "does not exist" in result.reason

    async def test_returns_0_when_path_is_directory(self) -> None:
        """Test that FileExists returns 0.0 when path is directory, not file."""
        with TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "subdir"
            test_dir.mkdir()

            evaluator = FileExists(path=str(test_dir))
            result = await evaluator.evaluate(MagicMock())

            assert result.value == 0.0
            assert "is not a file" in result.reason

    async def test_handles_relative_paths(self) -> None:
        """Test that FileExists handles relative paths."""
        with TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                test_file = Path("relative_file.txt")
                test_file.write_text("content")

                evaluator = FileExists(path="relative_file.txt")
                result = await evaluator.evaluate(MagicMock())

                assert result == 1.0
            finally:
                os.chdir(original_cwd)

    async def test_handles_absolute_paths(self) -> None:
        """Test that FileExists handles absolute paths."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "absolute_file.txt"
            test_file.write_text("content")

            evaluator = FileExists(path=str(test_file.absolute()))
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0

    async def test_handles_nested_paths(self) -> None:
        """Test that FileExists handles nested directory paths."""
        with TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "subdir"
            nested_dir.mkdir(parents=True)
            test_file = nested_dir / "file.txt"
            test_file.write_text("content")

            evaluator = FileExists(path=str(test_file))
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0


class TestContentMatches:
    """Tests for ContentMatches evaluator."""

    async def test_returns_1_when_pattern_matches(self) -> None:
        """Test that ContentMatches returns 1.0 when pattern matches."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("The port is 8080")

            evaluator = ContentMatches(path=str(test_file), pattern=r"port.*8080")
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0

    async def test_returns_0_when_pattern_does_not_match(self) -> None:
        """Test that ContentMatches returns 0.0 when pattern doesn't match."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("The port is 3000")

            evaluator = ContentMatches(path=str(test_file), pattern=r"port.*8080")
            result = await evaluator.evaluate(MagicMock())

            assert result.value == 0.0
            assert "does not match pattern" in result.reason

    async def test_returns_0_when_file_does_not_exist(self) -> None:
        """Test that ContentMatches returns 0.0 when file doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "nonexistent.txt"

            evaluator = ContentMatches(path=str(test_file), pattern=r".*")
            result = await evaluator.evaluate(MagicMock())

            assert result.value == 0.0
            assert "does not exist" in result.reason

    async def test_returns_0_when_path_is_directory(self) -> None:
        """Test that ContentMatches returns 0.0 when path is directory."""
        with TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "subdir"
            test_dir.mkdir()

            evaluator = ContentMatches(path=str(test_dir), pattern=r".*")
            result = await evaluator.evaluate(MagicMock())

            assert result.value == 0.0
            assert "is not a file" in result.reason

    async def test_handles_regex_special_characters(self) -> None:
        """Test that ContentMatches handles regex special characters correctly."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Price: $19.99 (20% off)")

            # Test with escaped special characters
            evaluator = ContentMatches(path=str(test_file), pattern=r"\$19\.99.*20%")
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0

    async def test_handles_multiline_content(self) -> None:
        """Test that ContentMatches handles multiline content."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Line 1\nLine 2\nLine 3")

            evaluator = ContentMatches(path=str(test_file), pattern=r"Line 1.*Line 3")
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0

    async def test_handles_unicode_content(self) -> None:
        """Test that ContentMatches handles unicode content."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("晴天 2.576", encoding="utf-8")

            evaluator = ContentMatches(path=str(test_file), pattern=r"晴天.*2\.576")
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0

    async def test_handles_permission_error_gracefully(self) -> None:
        """Test that ContentMatches handles PermissionError gracefully."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            # Make file unreadable (Unix only)
            if os.name != "nt":
                test_file.chmod(0o000)
                try:
                    evaluator = ContentMatches(path=str(test_file), pattern=r".*")
                    result = await evaluator.evaluate(MagicMock())

                    assert result.value == 0.0
                    assert "Error reading file" in result.reason
                finally:
                    test_file.chmod(0o644)

    async def test_case_sensitive_matching(self) -> None:
        """Test that ContentMatches is case sensitive by default."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello World")

            # Case sensitive - should not match
            evaluator = ContentMatches(path=str(test_file), pattern=r"hello")
            result = await evaluator.evaluate(MagicMock())

            assert result.value == 0.0

            # Case sensitive - should match
            evaluator = ContentMatches(path=str(test_file), pattern=r"Hello")
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0

    async def test_empty_file_handling(self) -> None:
        """Test that ContentMatches handles empty files."""
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.txt"
            test_file.write_text("")

            # Pattern that matches empty string
            evaluator = ContentMatches(path=str(test_file), pattern=r"^$")
            result = await evaluator.evaluate(MagicMock())

            assert result == 1.0

            # Pattern that doesn't match empty string
            evaluator = ContentMatches(path=str(test_file), pattern=r".+")
            result = await evaluator.evaluate(MagicMock())

            assert result.value == 0.0
