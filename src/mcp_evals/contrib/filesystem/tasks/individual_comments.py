"""Individual Comments task for filesystem domain."""

import csv
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected data based on answer.csv
EXPECTED_DATA = {
    "Bill Harvey": ["0", "2", "3", "1", "1", "1"],
    "Michelle Jackson": ["0", "1", "2", "1", "1", "1"],
    "David Russel": ["2", "1", "1", "2", "1", "1"],
    "Tony Taylor": ["2", "0", "1", "2", "1", "1"],
}

# Expected header columns (excluding first column which can be anything)
EXPECTED_HEADER_COLUMNS = ["1.1", "1.3", "4.6", "4.16", "6.8", "6.16"]

EXPECTED_COLUMN_COUNT = 7  # First column + 6 clauses


@dataclass
class OutputFileExists(Evaluator["IndividualCommentsTask", AgentRunResult]):
    """Evaluator that checks individual_comment.csv file exists."""

    async def evaluate(self, ctx: EvaluatorContext["IndividualCommentsTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the individual_comment.csv file exists."""
        task = ctx.inputs
        output_file = task.work_dir / "individual_comment.csv"

        if not output_file.exists():
            return EvaluationReason(value=0.0, reason="File 'individual_comment.csv' not found")

        return 1.0


@dataclass
class CSVFormat(Evaluator["IndividualCommentsTask", AgentRunResult]):
    """Evaluator that checks CSV file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext["IndividualCommentsTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the CSV file has the correct format."""
        task = ctx.inputs
        output_file = task.work_dir / "individual_comment.csv"

        try:
            with output_file.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                if not rows:
                    return EvaluationReason(value=0.0, reason="CSV file is empty")

                if len(rows) < 2:
                    return EvaluationReason(value=0.0, reason="CSV file has insufficient rows")

                header = rows[0]
                if len(header) != EXPECTED_COLUMN_COUNT:
                    return EvaluationReason(
                        value=0.0,
                        reason=(
                            f"Header row has incorrect number of columns: "
                            f"{len(header)}, expected {EXPECTED_COLUMN_COUNT}"
                        ),
                    )

                for i, row in enumerate(rows[1:], 1):
                    if len(row) != EXPECTED_COLUMN_COUNT:
                        return EvaluationReason(
                            value=0.0,
                            reason=(
                                f"Data row {i} has incorrect number of columns: "
                                f"{len(row)}, expected {EXPECTED_COLUMN_COUNT}"
                            ),
                        )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading CSV file: {e}")

        return 1.0


@dataclass
class CSVContent(Evaluator["IndividualCommentsTask", AgentRunResult]):
    """Evaluator that checks CSV content matches expected answer exactly."""

    async def evaluate(self, ctx: EvaluatorContext["IndividualCommentsTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: PLR0911
        """Verify that the CSV content matches the expected answer exactly."""
        task = ctx.inputs
        output_file = task.work_dir / "individual_comment.csv"

        try:
            with output_file.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                header = rows[0]
                if len(header) != EXPECTED_COLUMN_COUNT:
                    return EvaluationReason(
                        value=0.0,
                        reason=(
                            f"Header row has incorrect number of columns: "
                            f"{len(header)}, expected {EXPECTED_COLUMN_COUNT}"
                        ),
                    )

                # Check if all expected clause columns are present (allow order to be different)
                header_clauses = header[1:7]
                missing_clauses = []
                for expected_clause in EXPECTED_HEADER_COLUMNS:
                    if expected_clause not in header_clauses:
                        missing_clauses.append(expected_clause)

                if missing_clauses:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing expected clause columns: {missing_clauses}",
                    )

                extra_clauses = []
                for clause in header_clauses:
                    if clause not in EXPECTED_HEADER_COLUMNS:
                        extra_clauses.append(clause)

                if extra_clauses:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Unexpected extra clause columns: {extra_clauses}",
                    )

                # Create a mapping from expected clause order to actual column indices
                clause_mapping: dict[str, int] = {}
                for i, clause in enumerate(header_clauses):
                    if clause in EXPECTED_HEADER_COLUMNS:
                        clause_mapping[clause] = i

                # Parse the CSV data into a dictionary with correct column mapping
                csv_data: dict[str, list[str]] = {}
                for row in rows[1:]:
                    if len(row) >= EXPECTED_COLUMN_COUNT:
                        name = row[0]
                        # Map values according to the expected clause order
                        values = []
                        for expected_clause in EXPECTED_HEADER_COLUMNS:
                            col_index = clause_mapping[expected_clause] + 1
                            values.append(row[col_index])
                        csv_data[name] = values

                # Check if all expected names are present
                missing_names = []
                for expected_name in EXPECTED_DATA:
                    if expected_name not in csv_data:
                        missing_names.append(expected_name)

                if missing_names:
                    return EvaluationReason(value=0.0, reason=f"Missing expected names: {missing_names}")

                extra_names = []
                for name in csv_data:
                    if name not in EXPECTED_DATA:
                        extra_names.append(name)

                if extra_names:
                    return EvaluationReason(value=0.0, reason=f"Unexpected extra names: {extra_names}")

                # Check values for each person
                for name, expected_values in EXPECTED_DATA.items():
                    actual_values = csv_data[name]

                    if actual_values != expected_values:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"Values mismatch for {name}. Expected: {expected_values}, Got: {actual_values}",
                        )

        except (OSError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying CSV content: {e}")

        return 1.0


@dataclass
class DataAccuracy(Evaluator["IndividualCommentsTask", AgentRunResult]):
    """Evaluator that checks data values are accurate (all values are non-negative integers)."""

    async def evaluate(self, ctx: EvaluatorContext["IndividualCommentsTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the data values are accurate (all values are non-negative integers)."""
        task = ctx.inputs
        output_file = task.work_dir / "individual_comment.csv"

        try:
            with output_file.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                # Skip header row
                for i, row in enumerate(rows[1:], 1):
                    if len(row) >= EXPECTED_COLUMN_COUNT:
                        # Check all clause columns (skip first column which is name)
                        for j, value in enumerate(row[1:EXPECTED_COLUMN_COUNT], 1):
                            try:
                                int_value = int(value)
                                if int_value < 0:
                                    return EvaluationReason(
                                        value=0.0,
                                        reason=f"Row {i}, column {j} has negative value: {value}",
                                    )
                            except ValueError:
                                return EvaluationReason(
                                    value=0.0,
                                    reason=f"Row {i}, column {j} has non-integer value: {value}",
                                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking data accuracy: {e}")

        return 1.0


class IndividualCommentsTask(FilesystemTask):
    """Task for counting individual comments by person and clause.

    The agent must:
    1. Count comments by Bill Harvey, Michelle Jackson, David Russel, Tony Taylor
    2. Count comments in clauses 1.1, 1.3, 4.6, 4.16, 6.8, 6.16
    3. Focus on versions 5-8
    4. Generate individual_comment.csv with correct format
    """

    name = "individual_comments"
    goal = """Please use FileSystem tools to finish the following task:

**Overview**

The folder "legal_files/" contains all versions (Preferred_Stock_Purchase_Agreement_v0.txt -- Preferred_Stock_Purchase_Agreement_v10.txt) of the Stock Purchase Agreement for a corporate investment project.

There are comments in it, come from four people:
- **Bill Harvey** (Company CEO)
- **Michelle Jackson** (Investor)
- **David Russel** (Company Counsel)
- **Tony Taylor** (Investor Counsel)

Between v1 and v9, these four people make comments on the clauses. The comment format is `[name:content]`, where:
- `name` is the commenter's name
- `content` is the revision note

**Special Note:** If the name is "All parties", it represents a joint comment from all parties, which counts as one comment but does not count toward any individual's personal comment count.

## Task

Your task is to count the number of comments made by Bill Harvey (Company CEO), Michelle Jackson (Investor), David Russel (Company Counsel), and Tony Taylor (Investor Counsel) in clauses 1.1, 1.3, 4.6, 4.16, 6.8, and 6.16 **in version 5-8.** Please generate `individual_comment.csv` in the **main directory** where the first row contains these clauses (1.1, 1.3, 4.6, 4.16, 6.8, 6.16) and the first column contains the four names (Bill Harvey, Michelle Jackson, David Russel, Tony Taylor). Fill in the table with the number of comments for each person and each clause. If there are no comments, write 0."""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            OutputFileExists(),
            CSVFormat(),
            CSVContent(),
            DataAccuracy(),
        )
