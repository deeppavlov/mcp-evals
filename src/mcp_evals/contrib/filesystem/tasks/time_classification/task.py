"""Time Classification task for filesystem domain."""

from pathlib import Path

from pydantic_evals.evaluators import EvaluationReason

from mcp_evals.contrib.filesystem.common_evaluators import NoFilesInRoot, TotalFileCountAcrossDirectories
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.tasks.time_classification.constants import (
    DAY_MAPPING,
    EXPECTED_STRUCTURE,
    MONTH_MAPPING,
    SYSTEM_FILES,
    TOTAL_EXPECTED_FILES,
)
from mcp_evals.contrib.filesystem.tasks.time_classification.custom_evaluators import (
    DirectoryStructure,
    FilesInDirectories,
    MetadataAnalysisFiles,
)
from mcp_evals.contrib.filesystem.utils import Fixture


def find_month_directory(work_dir: Path, expected_month: str) -> Path | None:
    """Find the actual month directory, handling both numeric and alphabetic representations."""
    valid_month_names = MONTH_MAPPING.get(expected_month, [expected_month])

    for month_name in valid_month_names:
        month_dir = work_dir / month_name
        if month_dir.exists() and month_dir.is_dir():
            return month_dir

    return None


def find_day_directory(month_dir: Path, expected_day: str) -> Path | None:
    """Find the actual day directory, handling both numeric representations."""
    valid_day_names = DAY_MAPPING.get(expected_day, [expected_day])

    for day_name in valid_day_names:
        day_dir = month_dir / day_name
        if day_dir.exists() and day_dir.is_dir():
            return day_dir

    return None


def _get_expected_filename(expected_month: str, day: str, line_num: int) -> str | list[str] | None:
    """Get expected filename(s) for a given month/day/line combination."""
    if expected_month == "07" and day == "09":
        return "sg.jpg"
    if expected_month == "07" and day == "25":
        return "bus.mov"
    if expected_month == "07" and day == "26":
        return "road.mov"
    if expected_month == "08" and day == "06":
        if line_num == 1:
            return "bear.jpg"
        return ["random_file_1.txt", "random_file_2.txt", "random_file_3.txt"]
    return None


def _get_month_letters(expected_month: str) -> list[str] | None:
    """Get month letters for a given month."""
    if expected_month == "07":
        return ["jul", "7"]
    if expected_month == "08":
        return ["aug", "8"]
    return None


def _validate_metadata_line(
    line: str,
    line_num: int,
    expected_month: str,
    day: str,
    month_dir_name: str,
    day_dir_name: str,
) -> EvaluationReason | None:
    """Validate a single line from metadata_analyse.txt."""
    line_lower = line.lower()

    # Check filename
    expected_filename = _get_expected_filename(expected_month, day, line_num)
    if expected_filename is None:
        pass  # No filename requirement for this line
    elif isinstance(expected_filename, list):
        if not any(filename in line_lower for filename in expected_filename):
            msg = (
                f"Line {line_num} in '{month_dir_name}/{day_dir_name}' "
                f"should contain one of {expected_filename}: {line}"
            )
            return EvaluationReason(value=0.0, reason=msg)
    elif expected_filename not in line_lower:
        msg = f"Line {line_num} in '{month_dir_name}/{day_dir_name}' should contain '{expected_filename}': {line}"
        return EvaluationReason(value=0.0, reason=msg)

    # Check month letters
    month_letters = _get_month_letters(expected_month)
    if month_letters and not any(letter in line_lower for letter in month_letters):
        msg = f"Line {line_num} in '{month_dir_name}/{day_dir_name}' should contain month letters: {line}"
        return EvaluationReason(value=0.0, reason=msg)

    # Check year (2025)
    if "2025" not in line_lower:
        msg = f"Line {line_num} in '{month_dir_name}/{day_dir_name}' should contain '2025': {line}"
        return EvaluationReason(value=0.0, reason=msg)

    # Check day number
    valid_day_names = DAY_MAPPING.get(day, [day])
    if not any(day_name in line_lower for day_name in valid_day_names):
        msg = (
            f"Line {line_num} in '{month_dir_name}/{day_dir_name}' "
            f"should contain day '{day}' (or {valid_day_names}): {line}"
        )
        return EvaluationReason(value=0.0, reason=msg)

    return None


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
