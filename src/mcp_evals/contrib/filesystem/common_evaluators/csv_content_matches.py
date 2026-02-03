"""Common evaluators shared across filesystem tasks."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class CSVContentMatches(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks CSV content matches expected answer exactly.

    Validates that a CSV file has:
    - Correct column count
    - Expected header columns (excluding first column which can be anything)
    - All expected rows present with correct values
    - No extra rows or columns

    Example:
        CSVContentMatches(
            file_path="individual_comment.csv",
            expected_data={"Bill Harvey": ["0", "2", "3", "1", "1", "1"]},
            expected_header_columns=["1.1", "1.3", "4.6", "4.16", "6.8", "6.16"],
            expected_column_count=7,
            header_start_index=1,
        )
    """

    file_path: str
    expected_data: dict[str, list[str]]
    expected_header_columns: list[str]
    expected_column_count: int
    header_start_index: int = 1

    def _validate_header(self, header: list[str]) -> EvaluatorOutput | None:
        """Validate CSV header structure."""
        if len(header) != self.expected_column_count:
            return EvaluationReason(
                value=0.0,
                reason=(
                    f"Header row has incorrect number of columns: {len(header)}, expected {self.expected_column_count}"
                ),
            )

        header_columns = header[self.header_start_index : self.expected_column_count]
        missing_columns = [col for col in self.expected_header_columns if col not in header_columns]

        if missing_columns:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing expected columns: {missing_columns}",
            )

        extra_columns = [col for col in header_columns if col not in self.expected_header_columns]

        if extra_columns:
            return EvaluationReason(
                value=0.0,
                reason=f"Unexpected extra columns: {extra_columns}",
            )

        return None

    def _parse_csv_data(self, rows: list[list[str]], header: list[str]) -> dict[str, list[str]]:
        """Parse CSV data into a dictionary."""
        header_columns = header[self.header_start_index : self.expected_column_count]
        column_mapping: dict[str, int] = {
            col: i for i, col in enumerate(header_columns) if col in self.expected_header_columns
        }
        csv_data: dict[str, list[str]] = {}
        for row in rows[1:]:
            if len(row) >= self.expected_column_count:
                row_key = row[0]  # First column is the row identifier
                values = [
                    row[column_mapping[expected_col] + self.header_start_index]
                    for expected_col in self.expected_header_columns
                ]
                csv_data[row_key] = values
        return csv_data

    def _validate_data(self, csv_data: dict[str, list[str]]) -> EvaluatorOutput | None:
        """Validate CSV data matches expected values."""
        missing_keys = [key for key in self.expected_data if key not in csv_data]

        if missing_keys:
            return EvaluationReason(value=0.0, reason=f"Missing expected rows: {missing_keys}")

        extra_keys = [key for key in csv_data if key not in self.expected_data]

        if extra_keys:
            return EvaluationReason(value=0.0, reason=f"Unexpected extra rows: {extra_keys}")

        for key, expected_values in self.expected_data.items():
            actual_values = csv_data[key]

            if actual_values != expected_values:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Values mismatch for {key}. Expected: {expected_values}, Got: {actual_values}",
                )

        return None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the CSV content matches the expected answer exactly."""
        task = ctx.inputs
        output_file = task.work_dir / Path(self.file_path)

        if not output_file.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"CSV file '{self.file_path}' does not exist",
            )

        try:
            with output_file.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                if not rows:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"CSV file '{self.file_path}' is empty",
                    )

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
