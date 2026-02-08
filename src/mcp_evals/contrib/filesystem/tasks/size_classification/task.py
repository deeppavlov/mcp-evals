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
