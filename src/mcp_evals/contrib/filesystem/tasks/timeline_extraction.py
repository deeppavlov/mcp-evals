"""Timeline Extraction task for filesystem domain."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileContentStructure, FileExists, FileReadable
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected entries from answer.txt
EXPECTED_ENTRIES = {
    "exp_logs/project_2/analysis_report.md:2024-01-01",
    "learning/2024/learning_progress.csv:2024-01-01",
    "exp_logs/experiment_summary.md:2024-01-05",
    "play/kit&shoes_collection/inventory.py:2024-01-05",
    "exp_logs/experiment_summary.md:2024-01-10",
    "play/kit&shoes_collection/inventory.py:2024-01-10",
    "exp_logs/aug/augmentation_log.txt:2024-01-15",
    "exp_logs/experiment_summary.md:2024-01-15",
    "play/kit&shoes_collection/inventory.py:2024-01-15",
    "learning/2024/learning_progress.csv:2024-02-01",
    "learning/2024/learning_progress.csv:2024-03-01",
    "play/hongkong_tour/travel_itinerary.csv:2024-03-15",
    "travel_plan/travel_calculator.py:2024-03-15",
    "play/hongkong_tour/travel_itinerary.csv:2024-03-16",
    "play/hongkong_tour/travel_itinerary.csv:2024-03-17",
    "play/hongkong_tour/travel_itinerary.csv:2024-03-18",
    "play/hongkong_tour/travel_itinerary.csv:2024-03-19",
    "play/hongkong_tour/travel_itinerary.csv:2024-03-20",
    "travel_plan/travel_bucket_list.md:2024-04-01",
    "learning/2024/learning_progress.csv:2024-04-01",
    "learning/2024/learning_progress.csv:2024-05-01",
    "travel_plan/travel_bucket_list.md:2024-06-01",
    "learning/2024/learning_progress.csv:2024-06-01",
    "learning/2024/learning_progress.csv:2024-07-01",
    "exp_logs/exp_record.md:2024-08-01",
    "exp_logs/results_record.csv:2024-08-01",
    "travel_plan/travel_bucket_list.md:2024-08-01",
    "learning/2024/learning_progress.csv:2024-08-01",
    "exp_logs/results_record.csv:2024-08-02",
    "exp_logs/results_record.csv:2024-08-03",
    "exp_logs/results_record.csv:2024-08-04",
    "exp_logs/exp_record.md:2024-09-01",
    "exp_logs/sep/september_summary.csv:2024-09-01",
    "learning/2024/learning_progress.csv:2024-09-01",
    "exp_logs/sep/september_summary.csv:2024-09-05",
    "exp_logs/sep/september_summary.csv:2024-09-10",
    "exp_logs/sep/september_summary.csv:2024-09-15",
    "exp_logs/sep/september_summary.csv:2024-09-20",
    "exp_logs/sep/september_summary.csv:2024-09-25",
    "exp_logs/sep/september_summary.csv:2024-09-30",
    "learning/2024/learning_progress.csv:2024-10-01",
    "learning/2024/learning_progress.csv:2024-11-01",
    "learning/2024/learning_progress.csv:2024-12-01",
}

EXPECTED_LINE_COUNT = 43


@dataclass
class LineCount(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks timeline.txt file has exactly 43 lines."""

    async def evaluate(self, ctx: EvaluatorContext["TimelineExtractionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the timeline.txt file has exactly 43 lines."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            if len(lines) != EXPECTED_LINE_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Expected {EXPECTED_LINE_COUNT} lines, but found {len(lines)} lines",
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking line count: {e}")

        return 1.0


def _has_path_like_content(line: str) -> bool:
    """Check if a line contains path-like content."""
    # Method 1: Split into words and look for path-like content
    words = line.split()
    for word in words:
        if ("/" in word or "." in word) and not re.match(r"^\d{4}-\d{2}-\d{2}$", word.strip()):
            return True

    # Method 2: Check if line contains path-like content with colon separator
    if ":" in line:
        parts = line.split(":")
        for part in parts:
            if ("/" in part or "." in part) and not re.match(r"^\d{4}-\d{2}-\d{2}$", part.strip()):
                return True

    return False


@dataclass
class LineFormat(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks each line contains both file path and date time information."""

    async def evaluate(self, ctx: EvaluatorContext["TimelineExtractionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that each line contains both file path and date time information."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            date_pattern = r"\d{4}-\d{2}-\d{2}"  # YYYY-MM-DD format

            invalid_lines = []
            for i, line in enumerate(lines, 1):
                # Check if line contains a date
                if not re.search(date_pattern, line):
                    invalid_lines.append(f"Line {i}: '{line}' (no valid date found)")
                    continue

                # Check if line contains path-like content
                if not _has_path_like_content(line):
                    invalid_lines.append(f"Line {i}: '{line}' (no valid path found)")

            if invalid_lines:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Invalid line format found: {invalid_lines[:5]}",
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking line format: {e}")

        return 1.0


@dataclass
class DateFormat(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks all dates are in valid YYYY-MM-DD format."""

    async def evaluate(self, ctx: EvaluatorContext["TimelineExtractionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all dates are in valid YYYY-MM-DD format."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            invalid_dates = []
            for i, line in enumerate(lines, 1):
                try:
                    date_match = re.search(r"\d{4}-\d{2}-\d{2}", line)
                    if not date_match:
                        invalid_dates.append(f"Line {i}: '{line}' (no date found)")
                        continue

                    date_part = date_match.group()
                    datetime.strptime(date_part, "%Y-%m-%d")  # noqa: DTZ007
                except (ValueError, IndexError) as e:
                    invalid_dates.append(f"Line {i}: '{line}' (invalid date: {e})")

            if invalid_dates:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Invalid date format found: {invalid_dates[:5]}",
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking date format: {e}")

        return 1.0


@dataclass
class ChronologicalOrder(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks dates are in chronological order."""

    async def evaluate(self, ctx: EvaluatorContext["TimelineExtractionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that dates are in chronological order."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            dates = []
            for line in lines:
                date_match = re.search(r"\d{4}-\d{2}-\d{2}", line)
                if date_match:
                    date_obj = datetime.strptime(date_match.group(), "%Y-%m-%d")  # noqa: DTZ007
                    dates.append(date_obj)

            # Check if dates are in ascending order
            for i in range(1, len(dates)):
                if dates[i] < dates[i - 1]:
                    date1 = dates[i - 1].strftime("%Y-%m-%d")
                    date2 = dates[i].strftime("%Y-%m-%d")
                    msg = f"Date order violation: {date1} comes after {date2}"
                    return EvaluationReason(value=0.0, reason=msg)
        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking chronological order: {e}")

        return 1.0


def _extract_path_from_line(line: str) -> str | None:
    """Extract file path from a timeline line."""
    words = line.split()
    for word in words:
        if ("/" in word or "." in word) and not re.match(r"^\d{4}-\d{2}-\d{2}$", word.strip()):
            return word
    return None


def _check_missing_entries(actual_lines: list[str]) -> list[str]:
    """Check for missing expected entries."""
    missing_entries = []
    for expected in EXPECTED_ENTRIES:
        expected_path, expected_date = expected.split(":")
        found = False

        for actual_line in actual_lines:
            if expected_path in actual_line and expected_date in actual_line:
                found = True
                break

        if not found:
            missing_entries.append(expected)
    return missing_entries


def _check_extra_entries(actual_lines: list[str]) -> list[str]:
    """Check for extra unexpected entries."""
    extra_entries = []
    for actual_line in actual_lines:
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", actual_line)
        if not date_match:
            continue

        actual_date = date_match.group()
        actual_path = _extract_path_from_line(actual_line)

        if not actual_path:
            continue

        # Find if this line matches any expected entry
        found_expected = False
        for expected in EXPECTED_ENTRIES:
            expected_path, expected_date = expected.split(":")
            if expected_path in actual_path and expected_date == actual_date:
                found_expected = True
                break

        if not found_expected:
            extra_entries.append(actual_line)
    return extra_entries


@dataclass
class ExpectedEntries(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks all expected entries from answer.txt are present."""

    async def evaluate(self, ctx: EvaluatorContext["TimelineExtractionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all expected entries from answer.txt are present."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            actual_lines = [line.strip() for line in content.split("\n") if line.strip()]

            missing_entries = _check_missing_entries(actual_lines)
            if missing_entries:
                msg = f"Missing {len(missing_entries)} expected entries. Examples: {missing_entries[:3]}"
                return EvaluationReason(value=0.0, reason=msg)

            extra_entries = _check_extra_entries(actual_lines)
            if extra_entries:
                msg = f"Found {len(extra_entries)} unexpected entries. Examples: {extra_entries[:3]}"
                return EvaluationReason(value=0.0, reason=msg)
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking expected entries: {e}")

        return 1.0


@dataclass
class NoDuplicates(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks there are no duplicate entries."""

    async def evaluate(self, ctx: EvaluatorContext["TimelineExtractionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that there are no duplicate entries."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            if len(lines) != len(set(lines)):
                return EvaluationReason(value=0.0, reason="Duplicate entries found in timeline.txt")
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking for duplicates: {e}")

        return 1.0


def _extract_file_path_from_line(line: str) -> str | None:
    """Extract file path from a timeline line and check if it exists."""
    # Method 1: Split by colon and check each part
    if ":" in line:
        parts = line.split(":")
        for part_ in parts:
            part = part_.strip()
            if part and ("/" in part or "." in part) and not re.match(r"^\d{4}-\d{2}-\d{2}$", part):
                return part

    # Method 2: Split into words and look for path-like content
    words = line.split()
    for word in words:
        word_ = word.strip()
        if ("/" in word_ or "." in word_) and not re.match(r"^\d{4}-\d{2}-\d{2}$", word_):
            return word_

    # Method 3: Use regex to find path-like patterns
    path_matches = re.findall(r"[a-zA-Z0-9_\-\.\/]+/[a-zA-Z0-9_\-\.\/]+", line)
    for match in path_matches:
        if "." in match or "/" in match:
            return str(match)

    return None


@dataclass
class FilePathsExist(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks all file paths mentioned in timeline.txt actually exist."""

    async def evaluate(self, ctx: EvaluatorContext["TimelineExtractionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all file paths mentioned in timeline.txt actually exist."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            missing_files = []
            for line in lines:
                file_path = _extract_file_path_from_line(line)
                if file_path:
                    full_path = task.work_dir / file_path
                    if not full_path.exists():
                        missing_files.append(file_path)

            if missing_files:
                msg = f"{len(missing_files)} referenced files do not exist. Examples: {missing_files[:3]}"
                return EvaluationReason(value=0.0, reason=msg)
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file paths: {e}")

        return 1.0


class TimelineExtractionTask(FilesystemTask):
    """Task for extracting timeline information from files.

    The agent must:
    1. Read all files under current path
    2. Extract time/plan information indicating 2024
    3. Create timeline.txt with file_path:time format
    4. Sort by chronological order
    """

    name = "timeline_extraction"
    goal = """Please use FileSystem tools to finish the following task:

Read all the files under current path, extract every time/plan information that clearly indicates 2024, and \
integrate them into a list and create a file in main directory called `timeline.txt`. Write the timeline in \
the file in the following format.

### Rules
- If a task only shows month without day, use the 1st day of that month
- If a task only shows year without month and day, skip it.
- If a file shows multiple tasks on the same date, count only once per date

### Output Format
- Each line format: `file_path:time`
    - `file_path`: The file path where this time information appears (**relative to the current path**)
    - `time`: Specific time, if it's a time period, write the start time (YYYY-MM-DD)

### Sorting Requirements
- Sort by chronological order"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("timeline.txt"),
            FileReadable("timeline.txt"),
            FileContentStructure("timeline.txt", expected_lines=EXPECTED_LINE_COUNT),
            LineFormat(),
            DateFormat(),
            ChronologicalOrder(),
            ExpectedEntries(),
            NoDuplicates(),
            FilePathsExist(),
        )
