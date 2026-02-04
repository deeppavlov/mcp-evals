"""Common evaluators shared across filesystem tasks."""

import csv
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class CSVFormat(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks CSV file has correct structure.

    Example:
    - `CSVFormat("individual_comment.csv", expected_columns=7)`
    - `CSVFormat("tracing.csv", expected_columns=5, min_rows=10)`
    """

    path: str
    expected_columns: int
    min_rows: int = 2

    def _validate_file_path(self, file_path: Path) -> EvaluatorOutput | None:
        """Validate that the file path exists and is a file."""
        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"CSV file '{self.path}' does not exist",
            )
        if not file_path.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.path}' is not a file",
            )
        return None

    def _validate_csv_structure(self, rows: list[list[str]]) -> EvaluatorOutput | None:
        """Validate CSV structure: row count, header, and data rows."""
        if not rows:
            return EvaluationReason(
                value=0.0,
                reason=f"CSV file '{self.path}' is empty",
            )

        if len(rows) < self.min_rows:
            return EvaluationReason(
                value=0.0,
                reason=(
                    f"CSV file '{self.path}' has insufficient rows: {len(rows)}, expected at least {self.min_rows}"
                ),
            )

        header = rows[0]
        if len(header) != self.expected_columns:
            return EvaluationReason(
                value=0.0,
                reason=(
                    f"Header row in '{self.path}' has incorrect number of columns: "
                    f"{len(header)}, expected {self.expected_columns}"
                ),
            )

        for i, row in enumerate(rows[1:], 1):
            if len(row) != self.expected_columns:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Data row {i} in '{self.path}' has incorrect number of columns: "
                        f"{len(row)}, expected {self.expected_columns}"
                    ),
                )

        return None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the CSV file has the correct format.

        Verifies:
        - File exists and is readable
        - Has at least min_rows rows (default 2: header + at least 1 data row)
        - Header row has expected_columns columns
        - All data rows have expected_columns columns
        """
        task = ctx.inputs
        file_path = task.work_dir / Path(self.path)

        validation_error = self._validate_file_path(file_path)
        if validation_error is not None:
            return validation_error

        try:
            with file_path.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                structure_error = self._validate_csv_structure(rows)
                if structure_error is not None:
                    return structure_error

                return 1.0
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading CSV file '{self.path}': {e}",
            )
