"""File Merging task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import (
    AlphabeticalOrder,
    CorrectFilesSelected,
    FileContentIntegrity,
    FilenameHeaders,
)


class FileMergingTask(FilesystemTask):
    """Task for merging smallest files in alphabetical order.

    The agent must:
    1. Identify the 10 smallest .txt files (excluding file_12.txt)
    2. Sort the selected files alphabetically by filename
    3. Merge the content into merged_content.txt
    4. Add file headers before each file's content
    5. Maintain the original content without modifications
    """

    name = "file_merging"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("merged_content.txt"),
            CorrectFilesSelected(),
            AlphabeticalOrder(),
            FilenameHeaders(),
            FileContentIntegrity(),
        )
