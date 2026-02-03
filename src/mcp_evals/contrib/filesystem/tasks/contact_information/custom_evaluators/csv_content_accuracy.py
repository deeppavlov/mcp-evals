"""CSVContentAccuracy evaluator for contact_information task."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.contact_information.constants import EXPECTED_DATA

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.contact_information.task import ContactInformationTask


@dataclass
class CSVContentAccuracy(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks CSV content contains all required data."""

    def _check_duplicate(self, row_name: str, found_entries: set[str]) -> EvaluatorOutput | None:
        """Check for duplicate entries."""
        if row_name in found_entries:
            return EvaluationReason(
                value=0.0,
                reason=f"Duplicate name found: '{row_name}'",
            )
        return None

    def _check_row_columns(
        self, row_name: str, row: dict[str, str], expected: dict[str, str]
    ) -> EvaluatorOutput | None:
        """Check that row columns match expected values."""
        for key, expected_value in expected.items():
            if key in row:
                actual_value = row[key] if row[key] else ""
                if actual_value != expected_value:
                    msg = f"Entry '{row_name}', column '{key}': expected '{expected_value}', got '{actual_value}'"
                    return EvaluationReason(value=0.0, reason=msg)
            else:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Entry '{row_name}' missing column '{key}'",
                )
        return None

    async def evaluate(self, ctx: EvaluatorContext[ContactInformationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the CSV content contains all required data."""
        task = ctx.inputs
        contact_file = task.work_dir / "contact_info.csv"

        try:
            with contact_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            expected_dict = {entry["Name"]: entry for entry in EXPECTED_DATA}

            found_entries: set[str] = set()
            for row in rows:
                row_name = row.get("Name", "")
                if not row_name:
                    continue

                if row_name in expected_dict:
                    duplicate_check = self._check_duplicate(row_name, found_entries)
                    if duplicate_check is not None:
                        return duplicate_check

                    found_entries.add(row_name)
                    expected = expected_dict[row_name]

                    column_check = self._check_row_columns(row_name, row, expected)
                    if column_check is not None:
                        return column_check

            if len(found_entries) != len(EXPECTED_DATA):
                missing = set(expected_dict.keys()) - found_entries
                return EvaluationReason(value=0.0, reason=f"Missing entries: {sorted(missing)}")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying CSV content: {e}")

        return 1.0

