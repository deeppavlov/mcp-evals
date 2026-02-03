"""Solution Tracing task for filesystem domain."""

import csv
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import CSVFormat, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected data based on answer.csv
EXPECTED_DATA = {
    "version_number": ["5", "6", "7", "8"],
    "name": ["Bill Harvey", "Michelle Jackson", "Michelle Jackson", "Tony Taylor"],
}

# Expected header columns (excluding first column which can be anything)
EXPECTED_HEADER_COLUMNS = ["4.6", "4.16", "6.8", "6.16"]

EXPECTED_COLUMN_COUNT = 5  # First column + 4 clauses


@dataclass
class CSVContent(Evaluator["SolutionTracingTask", AgentRunResult]):
    """Evaluator that checks CSV content matches expected answer exactly."""

    def _validate_header(self, header: list[str]) -> EvaluatorOutput | None:
        """Validate CSV header structure."""
        if len(header) != EXPECTED_COLUMN_COUNT:
            return EvaluationReason(
                value=0.0,
                reason=(f"Header row has incorrect number of columns: {len(header)}, expected {EXPECTED_COLUMN_COUNT}"),
            )

        header_clauses = header[1:5]
        missing_clauses = [
            expected_clause for expected_clause in EXPECTED_HEADER_COLUMNS if expected_clause not in header_clauses
        ]

        if missing_clauses:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing expected clause columns: {missing_clauses}",
            )

        extra_clauses = [clause for clause in header_clauses if clause not in EXPECTED_HEADER_COLUMNS]

        if extra_clauses:
            return EvaluationReason(
                value=0.0,
                reason=f"Unexpected extra clause columns: {extra_clauses}",
            )

        return None

    def _parse_csv_data(self, rows: list[list[str]], header: list[str]) -> dict[str, list[str]]:
        """Parse CSV data into a dictionary."""
        header_clauses = header[1:5]
        clause_mapping: dict[str, int] = {
            clause: i for i, clause in enumerate(header_clauses) if clause in EXPECTED_HEADER_COLUMNS
        }
        csv_data: dict[str, list[str]] = {}
        for row in rows[1:]:
            if len(row) >= EXPECTED_COLUMN_COUNT:
                row_type = row[0]  # version_number or name
                values = [row[clause_mapping[expected_clause] + 1] for expected_clause in EXPECTED_HEADER_COLUMNS]
                csv_data[row_type] = values
        return csv_data

    def _validate_data(self, csv_data: dict[str, list[str]]) -> EvaluatorOutput | None:
        """Validate CSV data matches expected values."""
        missing_types = [expected_type for expected_type in EXPECTED_DATA if expected_type not in csv_data]

        if missing_types:
            return EvaluationReason(value=0.0, reason=f"Missing expected row types: {missing_types}")

        extra_types = [row_type for row_type in csv_data if row_type not in EXPECTED_DATA]

        if extra_types:
            return EvaluationReason(value=0.0, reason=f"Unexpected extra row types: {extra_types}")

        for row_type, expected_values in EXPECTED_DATA.items():
            actual_values = csv_data[row_type]

            if actual_values != expected_values:
                reason_msg = f"Values mismatch for {row_type}. Expected: {expected_values}, Got: {actual_values}"
                return EvaluationReason(value=0.0, reason=reason_msg)

        return None

    async def evaluate(self, ctx: EvaluatorContext["SolutionTracingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the CSV content matches the expected answer exactly."""
        task = ctx.inputs
        output_file = task.work_dir / "tracing.csv"

        try:
            with output_file.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                header = rows[0]
                error = self._validate_header(header)
                if error is not None:
                    return error

                csv_data = self._parse_csv_data(rows, header)
                error = self._validate_data(csv_data)
                if error is not None:
                    return error

        except (OSError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying CSV content: {e}")

        return 1.0


@dataclass
class DataAccuracy(Evaluator["SolutionTracingTask", AgentRunResult]):
    """Evaluator that checks data values are accurate."""

    async def evaluate(self, ctx: EvaluatorContext["SolutionTracingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the data values are accurate."""
        task = ctx.inputs
        output_file = task.work_dir / "tracing.csv"

        try:
            with output_file.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                # Skip header row
                for i, row in enumerate(rows[1:], 1):
                    if len(row) >= EXPECTED_COLUMN_COUNT:
                        row_type = row[0]

                        # Check clause columns
                        for j, value in enumerate(row[1:EXPECTED_COLUMN_COUNT], 1):
                            if row_type == "version_number":
                                # Version numbers should be integers
                                try:
                                    int_value = int(value)
                                    if int_value < 0:
                                        return EvaluationReason(
                                            value=0.0,
                                            reason=f"Row {i}, column {j} has negative version number: {value}",
                                        )
                                except ValueError:
                                    return EvaluationReason(
                                        value=0.0,
                                        reason=f"Row {i}, column {j} has non-integer version number: {value}",
                                    )
                            elif row_type == "name" and (not value or not value.strip()):
                                return EvaluationReason(
                                    value=0.0,
                                    reason=f"Row {i}, column {j} has empty name: {value}",
                                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking data accuracy: {e}")

        return 1.0


class SolutionTracingTask(FilesystemTask):
    """Task for tracing solutions in legal documents.

    The agent must:
    1. Focus on clauses 4.6, 4.16, 6.8, 6.16 in v5-9
    2. Determine who first proposed the idea that led to final solution
    3. Determine in which version's comment it appeared
    4. Generate tracing.csv with version_number and name for each clause
    """

    name = "solution_tracing"
    goal = """Please use FileSystem tools to finish the following task:

### Overview

The folder "legal_files/" contains all versions
(Preferred_Stock_Purchase_Agreement_v0.txt -- Preferred_Stock_Purchase_Agreement_v10.txt)
of the Stock Purchase Agreement for a corporate investment project.

There are comments in it, come from four people:
- **Bill Harvey** (Company CEO)
- **Michelle Jackson** (Investor)
- **David Russel** (Company Counsel)
- **Tony Taylor** (Investor Counsel)

Between v1 and v9, these four people make comments on the clauses. The comment format is `[name:content]`, where:
- `name` is the commenter's name
- `content` is the revision note

**Special Note:** If the name is "All parties", it represents a joint comment from all parties,
which counts as one comment but does not count toward any individual's personal comment count.

### Task Description

**Your task is to focus on clauses 4.6, 4.16, 6.8, and 6.16 in v5-9** to determine:
1. Who first proposed the idea that eventually led to the final agreed solution
2. In which version's comment it appeared

**Important:** If the final solution was formed through multiple people's comments,
count as the originator the person whose comment first provided the core motivation
(or part of the idea) that shaped the final solution.
The key is to identify who initially proposed the motivation for the final solution.

### Output Requirements

**File Name:** `tracing.csv` (must be placed in the main directory)

**CSV Structure:**
- **First row** (excluding the top-left cell): `4.6, 4.16, 6.8, 6.16`
- **First column** (excluding the top-left cell): `version_number, name`
- **Remaining cells:** Fill in the `version_number`
  (the version in which the final solution was first proposed, only write a number without any other things)
  and the `name` (the person who proposed it) for each clause"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("tracing.csv"),
            CSVFormat("tracing.csv", expected_columns=EXPECTED_COLUMN_COUNT),
            CSVContent(),
            DataAccuracy(),
        )
