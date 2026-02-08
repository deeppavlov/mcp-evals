"""Dataset Comparison task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FileInDirectory
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import AnalysisFormat, CategoryCounts, RequiredCategories


class DatasetComparisonTask(FilesystemTask):
    """Task for comparing ScanNet and SUN RGB-D datasets.

    The agent must:
    1. Map ScanNet object categories to SUN RGB-D categories
    2. Calculate object counts for each SUN RGB-D category
    3. Generate analysis.txt with format: category name, count, empty line
    4. Include all 10 SUN RGB-D categories with correct counts
    """

    name = "dataset_comparison"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("analysis.txt"),
            FileInDirectory(
                file_path="analysis.txt",
                expected_directory=None,  # None means root/work_dir
            ),
            AnalysisFormat(),
            RequiredCategories(),
            CategoryCounts(),
        )
