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
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You are given a directory containing multiple text files of varying sizes. Your task is to identify the 10 smallest \
.txt files, merge their content in alphabetical order, and create a consolidated file called "merged_content.txt" \
with proper formatting.

### Task Objectives

1. **Identify the 10 smallest .txt files** in the test directory (excluding file_12.txt)
2. **Sort the selected files alphabetically** by filename
3. **Merge the content** of these files into a single file named `merged_content.txt`
4. **Add file headers** (file name) before each file's content
5. **Maintain the original content** of each file without modifications

### Expected Output

- File name: `merged_content.txt`
- Content should include all 10 files in alphabetical order
- Each file section should start with the filename
- Original file content should be preserved exactly"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("merged_content.txt"),
            CorrectFilesSelected(),
            AlphabeticalOrder(),
            FilenameHeaders(),
            FileContentIntegrity(),
        )

