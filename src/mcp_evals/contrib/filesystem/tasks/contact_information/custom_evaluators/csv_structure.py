"""CSVStructure evaluator for contact_information task."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.contact_information.task import ContactInformationTask


@dataclass
class CSVStructure(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks CSV file has correct structure."""

    def _validate_structure(self, rows: list[list[str]]) -> EvaluatorOutput | None:
        """Validate CSV structure and return error if invalid."""
        min_required_rows = 2
        if len(rows) < min_required_rows:
            return EvaluationReason(value=0.0, reason="CSV file has insufficient rows")

        headers = rows[0]
        if not headers:
            return EvaluationReason(value=0.0, reason="CSV file has no headers")

        if headers[0].lower() != "name":
            return EvaluationReason(value=0.0, reason="First column is not 'Name'")

        header_lower = [h.lower() for h in headers]
        if "email" not in header_lower:
            return EvaluationReason(value=0.0, reason="'Email' column not found")

        if "phone" not in header_lower:
            return EvaluationReason(value=0.0, reason="'Phone' column not found")

        return None

    async def evaluate(self, ctx: EvaluatorContext[ContactInformationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the CSV file has the correct structure."""
        task = ctx.inputs
        contact_file = task.work_dir / "contact_info.csv"

        try:
            with contact_file.open("r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            error = self._validate_structure(rows)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading CSV file: {e}")

        return 1.0

