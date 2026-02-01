"""Duplicates Searching task for filesystem domain."""

import hashlib
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals import Task
from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists, FileCount
from mcp_evals.contrib.filesystem.utils import Fixture, create_isolated_workspace, download_fixture

# Expected duplicate file groups
EXPECTED_DUPLICATE_GROUPS = {
    "group1": ["file_01.txt", "file_02.txt"],
    "group2": ["file_03.txt", "file_04.txt"],
    "group3": ["file_07.txt", "file_08.txt"],
    "group4": ["file_10.txt", "file_11.txt"],
    "group5": ["file_13.txt", "file_14.txt"],
    "group6": ["file_15.txt", "file_16.txt"],
    "group7": ["file_18.txt", "file_19.txt"],
}

# Expected unique files that should remain in original location
EXPECTED_UNIQUE_FILES = [
    "file_05.txt",
    "file_06.txt",
    "file_09.txt",
    "file_12.txt",
    "file_17.txt",
    "file_20.txt",
]


def calculate_file_hash(file_path: Path) -> str | None:
    """Calculate MD5 hash of file content."""
    try:
        with file_path.open("rb") as f:
            return hashlib.md5(f.read()).hexdigest()  # noqa: S324
    except (OSError, UnicodeDecodeError):
        return None


@dataclass
class DuplicateFilesMoved(Evaluator["DuplicatesSearchingTask", AgentRunResult]):
    """Evaluator that checks all duplicate files have been moved to duplicates directory."""

    async def evaluate(self, ctx: EvaluatorContext["DuplicatesSearchingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all duplicate files are in the duplicates directory."""
        task = ctx.inputs
        if not hasattr(task, "work_dir") or task.work_dir is None:
            return EvaluationReason(value=0.0, reason="Task work_dir not set")

        duplicates_dir = task.work_dir / "duplicates"

        if not duplicates_dir.exists():
            return EvaluationReason(value=0.0, reason="Duplicates directory does not exist")

        missing_files = []
        for files in EXPECTED_DUPLICATE_GROUPS.values():
            for filename in files:
                file_path = duplicates_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing duplicate files in 'duplicates' directory: {missing_files}",
            )

        return 1.0


@dataclass
class UniqueFilesRemain(Evaluator["DuplicatesSearchingTask", AgentRunResult]):
    """Evaluator that checks unique files remain in original location."""

    async def evaluate(self, ctx: EvaluatorContext["DuplicatesSearchingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that unique files remain in the original location."""
        task = ctx.inputs
        if not hasattr(task, "work_dir") or task.work_dir is None:
            return EvaluationReason(value=0.0, reason="Task work_dir not set")

        missing_files = []
        for filename in EXPECTED_UNIQUE_FILES:
            file_path = task.work_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing unique files in original location: {missing_files}",
            )

        return 1.0


@dataclass
class NoDuplicatesInOriginal(Evaluator["DuplicatesSearchingTask", AgentRunResult]):
    """Evaluator that checks no duplicate files remain in original location."""

    async def evaluate(self, ctx: EvaluatorContext["DuplicatesSearchingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that no duplicate files remain in the original location."""
        task = ctx.inputs
        if not hasattr(task, "work_dir") or task.work_dir is None:
            return EvaluationReason(value=0.0, reason="Task work_dir not set")

        remaining_duplicates = []
        for files in EXPECTED_DUPLICATE_GROUPS.values():
            for filename in files:
                file_path = task.work_dir / filename
                if file_path.exists():
                    remaining_duplicates.append(filename)

        if remaining_duplicates:
            return EvaluationReason(
                value=0.0,
                reason=f"Duplicate files still exist in original location: {remaining_duplicates}",
            )

        return 1.0


@dataclass
class ContentIntegrity(Evaluator["DuplicatesSearchingTask", AgentRunResult]):
    """Evaluator that checks file content integrity is maintained after moving."""

    async def evaluate(self, ctx: EvaluatorContext["DuplicatesSearchingTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: C901, PLR0911
        """Verify that files in each duplicate group have identical content."""
        task = ctx.inputs
        if not hasattr(task, "work_dir") or task.work_dir is None:
            return EvaluationReason(value=0.0, reason="Task work_dir not set")

        duplicates_dir = task.work_dir / "duplicates"

        if not duplicates_dir.exists():
            return EvaluationReason(value=0.0, reason="Duplicates directory does not exist")

        # Check that files in each duplicate group have identical content
        for group_name, files in EXPECTED_DUPLICATE_GROUPS.items():
            if len(files) < 2:  # noqa: PLR2004
                continue

            # Calculate hash of the first file in the group
            first_file = duplicates_dir / files[0]
            if not first_file.exists():
                return EvaluationReason(
                    value=0.0,
                    reason=f"First file of group {group_name} not found: {files[0]}",
                )

            first_hash = calculate_file_hash(first_file)
            if first_hash is None:
                return EvaluationReason(value=0.0, reason=f"Error calculating hash for {files[0]}")

            # Check that all other files in the group have the same hash
            for filename in files[1:]:
                file_path = duplicates_dir / filename
                if not file_path.exists():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"File in group {group_name} not found: {filename}",
                    )

                file_hash = calculate_file_hash(file_path)
                if file_hash is None:
                    return EvaluationReason(value=0.0, reason=f"Error calculating hash for {filename}")

                if file_hash != first_hash:
                    msg = f"Files in group {group_name} have different content: {files[0]} vs {filename}"
                    return EvaluationReason(value=0.0, reason=msg)

        return 1.0


class DuplicatesSearchingTask(Task):
    """Task for detecting and organizing duplicate files.

    The agent must:
    1. Scan all text files to identify groups with identical content
    2. Create a 'duplicates' directory
    3. Move all duplicate files into the 'duplicates' directory
    4. Leave unique files in their original location
    """

    name = "duplicates_searching"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You are given a directory containing multiple text files. Some files have identical content and need to be organized. \
Your task is to identify all files with duplicate content and move them to a newly created 'duplicates' directory.

### Task Objectives

1. **Scan all text files** in the test directory to identify groups with identical content
2. **Create a 'duplicates' directory** in the test directory root
3. **Move all duplicate files** into the 'duplicates' directory
4. **Leave unique files** in their original location

### Expected Output

After completing the task, the directory structure should be:

- `duplicates/` directory containing all files with duplicate content
- Original directory containing only files with unique content"""

    _stack: AsyncExitStack | None = None
    work_dir: Path | None = None

    def __init__(self) -> None:
        """Initialize the task with evaluators."""
        self.evaluators = (
            DirectoryExists("duplicates"),
            FileCount("duplicates", expected=14),
            DuplicateFilesMoved(),
            UniqueFilesRemain(),
            NoDuplicatesInOriginal(),
            ContentIntegrity(),
        )

    async def setup(self) -> None:
        """Set up the task environment."""
        if self._stack is not None:
            msg = f"Task {self.name} context already entered"
            raise RuntimeError(msg)

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        # Download fixture
        fixture_path = await download_fixture(Fixture.FILE_CONTEXT)

        # Create isolated workspace - enter context manager into stack
        workspace_ctx = create_isolated_workspace(fixture_path)
        self.work_dir = await self._stack.enter_async_context(workspace_ctx)

        # Set FILESYSTEM_ROOT for MCP server
        old_value = os.environ.get("FILESYSTEM_ROOT")
        os.environ["FILESYSTEM_ROOT"] = str(self.work_dir)
        self._stack.callback(self._restore_env, "FILESYSTEM_ROOT", old_value)

    async def teardown(self) -> None:
        """Clean up the task environment."""
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None

    @staticmethod
    def _restore_env(key: str, old_value: str | None) -> None:
        """Restore environment variable to previous value."""
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value
