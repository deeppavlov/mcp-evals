"""Size Classification task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import (
    DirectoriesExist,
    NoFilesInRoot,
    TotalFileCountAcrossDirectories,
)
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import REQUIRED_DIRS, SYSTEM_FILES, TOTAL_EXPECTED_FILES
from .custom_evaluators import FileClassification, FileSizes


class SizeClassificationTask(FilesystemTask):
    """Task for classifying files by size into three categories.

    The agent must:
    1. Create three directories: small_files/, medium_files/, large_files/
    2. Move files based on size: < 300 bytes, 300-700 bytes, > 700 bytes
    3. Ensure all files are classified correctly
    """

    name = "size_classification"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

Classify all files in the test directory into three categories based on their file size.
Create three subdirectories and move files accordingly.

### Task Objectives

1. **Create three directories** in the test directory:
   - `small_files/` - for files smaller than 300 bytes
   - `medium_files/` - for files between 300-700 bytes (inclusive)
   - `large_files/` - for files larger than 700 bytes

2. **Move all files** from the test directory into the appropriate subdirectory based on their size

3. **Handle all file types** - classify all files regardless of their extension (.txt, .jpg, .MOV, etc.)

### Expected Output

After completing the task, the directory structure should be:
- `small_files/` containing files < 300 bytes
- `medium_files/` containing files 300-700 bytes
- `large_files/` containing files > 700 bytes
- No files remain in the root test directory"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoriesExist(REQUIRED_DIRS),
            FileClassification(),
            NoFilesInRoot(SYSTEM_FILES),
            FileSizes(),
            TotalFileCountAcrossDirectories(REQUIRED_DIRS, TOTAL_EXPECTED_FILES, SYSTEM_FILES),
        )
