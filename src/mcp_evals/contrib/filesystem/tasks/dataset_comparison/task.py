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
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

Analyze the codebase to map ScanNet object categories to SUN RGB-D categories and calculate object counts.

### Task Objectives

1. **Primary Goal**: Use SUN RGB-D's 10-category classification system as the target taxonomy
2. **Mapping Requirement**: Map each ScanNet object category (using the "category" field, not "raw_category") to the \
corresponding SUN RGB-D category
3. **Calculation**: For each SUN RGB-D category, calculate the total count of objects from ScanNet that map to that \
category (It only counts if the category (not raw category) name are exactly the same (night_stand = nightstand))
4. **Output**: Generate an analysis.txt file in the main directory showing the mapping and counts

### Expected Output

Create a file named `analysis.txt` in the test directory root with the following format:

- Each SUN RGB-D category should be represented as a 2-line block
- Line 1: category name
- Line 2: total count
- Each block should be separated by one empty line

### Success Criteria

The analysis.txt file should contain all 10 SUN RGB-D categories:
chair, table, bed, bookshelf, desk, toilet, dresser, bathtub, sofa, night_stand

With correct counts:
- chair: 4681
- table: 1170
- bed: 370
- bookshelf: 377
- desk: 680
- toilet: 256
- dresser: 213
- bathtub: 144
- sofa: 1
- night_stand: 224"""

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
