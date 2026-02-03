"""Time Classification task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import NoFilesInRoot
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected directory structure
EXPECTED_STRUCTURE = {
    "07": {
        "09": ["sg.jpg"],
        "25": ["bus.MOV"],
        "26": ["road.MOV"],
    },
    "08": {
        "06": ["bear.jpg", "bridge.jpg", "random_file_1.txt", "random_file_2.txt", "random_file_3.txt"],
    },
}

# Month mapping (numeric and alphabetic)
MONTH_MAPPING = {
    "07": ["07", "7", "jul", "Jul", "JUL"],
    "08": ["08", "8", "aug", "Aug", "AUG"],
}

# Day mapping
DAY_MAPPING = {
    "09": ["09", "9"],
    "25": ["25"],
    "26": ["26"],
    "06": ["06", "6"],
}

# System files to ignore
SYSTEM_FILES = [".DS_Store", "Thumbs.db", ".DS_Store?", "._.DS_Store", "metadata_analyse.txt"]

TOTAL_EXPECTED_FILES = sum(len(files) for days in EXPECTED_STRUCTURE.values() for files in days.values())


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


@dataclass
class DirectoryStructure(Evaluator["TimeClassificationTask", AgentRunResult]):
    """Evaluator that checks correct directory structure exists."""

    async def evaluate(self, ctx: EvaluatorContext["TimeClassificationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the correct directory structure exists."""
        task = ctx.inputs

        for expected_month, days in EXPECTED_STRUCTURE.items():
            month_dir = find_month_directory(task.work_dir, expected_month)
            if month_dir is None:
                valid_names = MONTH_MAPPING.get(expected_month, [expected_month])
                return EvaluationReason(
                    value=0.0,
                    reason=f"Month directory not found. Expected one of: {valid_names}",
                )

            for day in days:
                day_dir = find_day_directory(month_dir, day)
                if day_dir is None:
                    valid_day_names = DAY_MAPPING.get(day, [day])
                    msg = f"Day directory '{month_dir.name}/{day}' not found. Expected one of: {valid_day_names}"
                    return EvaluationReason(value=0.0, reason=msg)

                if not day_dir.is_dir():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"'{month_dir.name}/{day_dir.name}' exists but is not a directory",
                    )

        return 1.0


@dataclass
class FilesInDirectories(Evaluator["TimeClassificationTask", AgentRunResult]):
    """Evaluator that checks files are in the correct directories."""

    async def evaluate(self, ctx: EvaluatorContext["TimeClassificationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are in the correct directories."""
        task = ctx.inputs

        for expected_month, days in EXPECTED_STRUCTURE.items():
            month_dir = find_month_directory(task.work_dir, expected_month)
            if month_dir is None:
                continue  # Already handled in DirectoryStructure

            for day, expected_files in days.items():
                day_dir = find_day_directory(month_dir, day)
                if day_dir is None:
                    continue  # Already handled in DirectoryStructure

                missing_files = []
                for filename in expected_files:
                    file_path = day_dir / filename
                    if not file_path.exists():
                        missing_files.append(filename)

                if missing_files:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing files in '{month_dir.name}/{day_dir.name}': {missing_files}",
                    )

                try:
                    actual_files = [f.name for f in day_dir.iterdir() if f.is_file()]
                    unexpected_files = [f for f in actual_files if f not in expected_files and f not in SYSTEM_FILES]

                    if unexpected_files:
                        msg = f"Unexpected files in '{month_dir.name}/{day_dir.name}': {unexpected_files}"
                        return EvaluationReason(value=0.0, reason=msg)
                except (OSError, PermissionError) as e:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Error reading directory '{month_dir.name}/{day_dir.name}': {e}",
                    )

        return 1.0


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


@dataclass
class MetadataAnalysisFiles(Evaluator["TimeClassificationTask", AgentRunResult]):
    """Evaluator that checks metadata_analyse.txt files exist and have correct content."""

    async def evaluate(self, ctx: EvaluatorContext["TimeClassificationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that metadata_analyse.txt files exist and have correct content."""
        task = ctx.inputs

        for expected_month, days in EXPECTED_STRUCTURE.items():
            month_dir = find_month_directory(task.work_dir, expected_month)
            if month_dir is None:
                continue  # Already handled in DirectoryStructure

            for day in days:
                day_dir = find_day_directory(month_dir, day)
                if day_dir is None:
                    continue  # Already handled in DirectoryStructure

                metadata_file = day_dir / "metadata_analyse.txt"

                if not metadata_file.exists():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"metadata_analyse.txt not found in '{month_dir.name}/{day_dir.name}'",
                    )

                try:
                    content = metadata_file.read_text(encoding="utf-8").strip()
                    lines = content.split("\n")

                    if len(lines) != 2:  # noqa: PLR2004
                        msg = (
                            f"metadata_analyse.txt in '{month_dir.name}/{day_dir.name}' "
                            f"has {len(lines)} lines, expected 2"
                        )
                        return EvaluationReason(value=0.0, reason=msg)

                    # Check each line
                    for line_num, line in enumerate(lines, 1):
                        error = _validate_metadata_line(
                            line, line_num, expected_month, day, month_dir.name, day_dir.name
                        )
                        if error:
                            return error

                except (OSError, UnicodeDecodeError) as e:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Error reading metadata_analyse.txt in '{month_dir.name}/{day_dir.name}': {e}",
                    )

        return 1.0


@dataclass
class TotalFileCount(Evaluator["TimeClassificationTask", AgentRunResult]):
    """Evaluator that checks all original files are accounted for."""

    async def evaluate(self, ctx: EvaluatorContext["TimeClassificationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all original files are accounted for."""
        task = ctx.inputs

        total_actual = 0
        for expected_month, days in EXPECTED_STRUCTURE.items():
            month_dir = find_month_directory(task.work_dir, expected_month)
            if month_dir is None:
                continue

            for day in days:
                day_dir = find_day_directory(month_dir, day)
                if day_dir and day_dir.exists():
                    try:
                        files_in_dir = [f for f in day_dir.iterdir() if f.is_file() and f.name not in SYSTEM_FILES]
                        total_actual += len(files_in_dir)
                    except (OSError, PermissionError):
                        continue

        if total_actual != TOTAL_EXPECTED_FILES:
            return EvaluationReason(
                value=0.0,
                reason=f"Expected {TOTAL_EXPECTED_FILES} files total, found {total_actual}",
            )

        return 1.0


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
        self.evaluators = (
            DirectoryStructure(),
            FilesInDirectories(),
            MetadataAnalysisFiles(),
            NoFilesInRoot(SYSTEM_FILES),
            TotalFileCount(),
        )
