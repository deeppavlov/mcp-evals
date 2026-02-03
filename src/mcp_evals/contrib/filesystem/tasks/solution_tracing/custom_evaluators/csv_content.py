"""CSVContent evaluator for solution_tracing task."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.solution_tracing.constants import (
    EXPECTED_COLUMN_COUNT,
    EXPECTED_DATA,
    EXPECTED_HEADER_COLUMNS,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.solution_tracing.task import SolutionTracingTask


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

    async def evaluate(self, ctx: EvaluatorContext[SolutionTracingTask, AgentRunResult]) -> EvaluatorOutput:
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
