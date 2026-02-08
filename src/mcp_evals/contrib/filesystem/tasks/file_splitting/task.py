"""File Splitting task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists, FilesExistInDirectory
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import EXPECTED_SPLIT_FILES
from .custom_evaluators import ContentIntegrity, EqualFileLengths, NoExtraFiles


class FileSplittingTask(FilesystemTask):
    """Task for splitting a large file into equal-sized smaller files.

    The agent must:
    1. Create a new directory named 'split'
    2. Split large_file.txt into exactly 10 files with equal character counts
    3. Name files as split_01.txt, split_02.txt, ..., split_10.txt
    4. Ensure equal distribution of characters
    5. Preserve content integrity
    """

    name = "file_splitting"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists("split"),
            FilesExistInDirectory("split", EXPECTED_SPLIT_FILES),
            EqualFileLengths(),
            ContentIntegrity(),
            NoExtraFiles(),
        )
