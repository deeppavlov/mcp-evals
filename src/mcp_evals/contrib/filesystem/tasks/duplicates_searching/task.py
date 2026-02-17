"""Duplicates Searching task for filesystem domain."""

from contextlib import AsyncExitStack
from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists, FileCount
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import ContentIntegrity, DuplicateFilesMoved, NoDuplicatesInOriginal, UniqueFilesRemain


class DuplicatesSearchingTask(FilesystemTask):
    """Task for detecting and organizing duplicate files.

    The agent must:
    1. Scan all text files to identify groups with identical content
    2. Create a 'duplicates' directory
    3. Move all duplicate files into the 'duplicates' directory
    4. Leave unique files in their original location
    """

    name = "duplicates_searching"

    _stack: AsyncExitStack | None = None

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            DirectoryExists("duplicates"),
            FileCount("duplicates", expected=14),
            DuplicateFilesMoved(),
            UniqueFilesRemain(),
            NoDuplicatesInOriginal(),
            ContentIntegrity(),
        )
