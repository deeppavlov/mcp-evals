"""Time Classification task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import NoFilesInRoot, TotalFileCountAcrossDirectories
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.tasks.time_classification.constants import (
    EXPECTED_STRUCTURE,
    SYSTEM_FILES,
    TOTAL_EXPECTED_FILES,
)
from mcp_evals.contrib.filesystem.tasks.time_classification.custom_evaluators import (
    DirectoryStructure,
    FilesInDirectories,
    MetadataAnalysisFiles,
)
from mcp_evals.contrib.filesystem.tasks.time_classification.utils import (
    find_day_directory,
    find_month_directory,
)
from mcp_evals.contrib.filesystem.utils import Fixture


class TimeClassificationTask(FilesystemTask):
    """Task for organizing files by creation time into hierarchical directory structure.

    The agent must:
    1. Read metadata of all files
    2. Analyze creation times (ctime)
    3. Create directory structure organized by month/day
    4. Move files to appropriate directories
    5. Create metadata_analyse.txt in each directory
    """

    name = "time_classification"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

Analyze the creation time (ctime) of all files in the test directory and organize them into a hierarchical \
directory structure based on their creation dates.

### Task Objectives

1. **Read metadata** of all files in the test directory
2. **Analyze creation times** (ctime) of all files (excluding .DS_Store)
3. **Create directory structure** organized by month/day based on creation time
4. **Move files** to appropriate directories
5. **Create metadata analysis files** in each directory

### Expected Output

#### Directory Structure

Create directories in the format: `MM/DD/` where:
- MM = month (two digits, e.g., 01, 02, or month name like Jul, Aug)
- DD = day (two digits, e.g., 07, 09, 11, 26)

#### Metadata Analysis Files

Create a file named `metadata_analyse.txt` in each directory containing exactly two lines:
- **Line 1**: Oldest filename and its creation time
- **Line 2**: Latest filename and its creation time

Each line should include the filename, month, day, and year (2025)."""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)

        # Create a custom resolver for nested month/day structure
        def resolve_nested_time_dirs(base_path: Path, key: str) -> Path | None:
            """Resolve nested directory structure for time classification.

            For first-level resolution (months), base_path is work_dir and key is month.
            For second-level resolution (days), base_path is month_dir and key is day.
            """
            # Check if key is a month (first level)
            if key in EXPECTED_STRUCTURE:
                return find_month_directory(base_path, key)
            # Otherwise, treat as day (second level) - base_path should be month_dir
            return find_day_directory(base_path, key)

        self.evaluators = (
            DirectoryStructure(),
            FilesInDirectories(),
            MetadataAnalysisFiles(),
            NoFilesInRoot(SYSTEM_FILES),
            TotalFileCountAcrossDirectories(
                directories=EXPECTED_STRUCTURE,
                expected_total=TOTAL_EXPECTED_FILES,
                system_files=SYSTEM_FILES,
                directory_resolver=resolve_nested_time_dirs,
            ),
        )
