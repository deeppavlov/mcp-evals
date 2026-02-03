"""Evaluator that checks CSV content matches expected answer exactly."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.individual_comments.constants import (
    EXPECTED_COLUMN_COUNT,
    EXPECTED_DATA,
    EXPECTED_HEADER_COLUMNS,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.individual_comments.task import IndividualCommentsTask


@dataclass
class CSVContent(Evaluator["IndividualCommentsTask", AgentRunResult]):
    """Evaluator that checks CSV content matches expected answer exactly."""

    def _validate_header(self, header: list[str]) -> EvaluatorOutput | None:
        """Validate CSV header structure."""
        if len(header) != EXPECTED_COLUMN_COUNT:
            return EvaluationReason(
                value=0.0,
                reason=(f"Header row has incorrect number of columns: {len(header)}, expected {EXPECTED_COLUMN_COUNT}"),
            )

        header_clauses = header[1:7]
        missing_clauses = [e for e in EXPECTED_HEADER_COLUMNS if e not in header_clauses]

        if missing_clauses:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing expected clause columns: {missing_clauses}",
            )

        extra_clauses = [c for c in header_clauses if c not in EXPECTED_HEADER_COLUMNS]

        if extra_clauses:
            return EvaluationReason(
                value=0.0,
                reason=f"Unexpected extra clause columns: {extra_clauses}",
            )

        return None

    def _parse_csv_data(self, rows: list[list[str]], header: list[str]) -> dict[str, list[str]]:
        """Parse CSV data into a dictionary."""
        header_clauses = header[1:7]
        clause_mapping: dict[str, int] = {c: i for i, c in enumerate(header_clauses) if c in EXPECTED_HEADER_COLUMNS}
        csv_data: dict[str, list[str]] = {}
        for row in rows[1:]:
            if len(row) >= EXPECTED_COLUMN_COUNT:
                name = row[0]
                values = []
                for expected_clause in EXPECTED_HEADER_COLUMNS:
                    col_index = clause_mapping[expected_clause] + 1
                    values.append(row[col_index])
                csv_data[name] = values
        return csv_data

    def _validate_data(self, csv_data: dict[str, list[str]]) -> EvaluatorOutput | None:
        """Validate CSV data matches expected values."""
        missing_names = [e for e in EXPECTED_DATA if e not in csv_data]

        if missing_names:
            return EvaluationReason(value=0.0, reason=f"Missing expected names: {missing_names}")

        extra_names = [name for name in csv_data if name not in EXPECTED_DATA]

        if extra_names:
            return EvaluationReason(value=0.0, reason=f"Unexpected extra names: {extra_names}")

        for name, expected_values in EXPECTED_DATA.items():
            actual_values = csv_data[name]

            if actual_values != expected_values:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Values mismatch for {name}. Expected: {expected_values}, Got: {actual_values}",
                )

        return None

    async def evaluate(self, ctx: EvaluatorContext[IndividualCommentsTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the CSV content matches the expected answer exactly."""
        task = ctx.inputs
        output_file = task.work_dir / "individual_comment.csv"

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
