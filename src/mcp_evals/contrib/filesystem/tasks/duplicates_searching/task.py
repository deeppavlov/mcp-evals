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

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists("duplicates"),
            FileCount("duplicates", expected=14),
            DuplicateFilesMoved(),
            UniqueFilesRemain(),
            NoDuplicatesInOriginal(),
            ContentIntegrity(),
        )
