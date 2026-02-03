"""CSVDataCompleteness evaluator for contact_information task."""

import csv
from dataclasses import dataclass

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.contact_information.constants import EXPECTED_NAMES


@dataclass
class CSVDataCompleteness(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks all required data is present and no entries are missing."""

    async def evaluate(self, ctx: EvaluatorContext["ContactInformationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required data is present and no entries are missing."""
        task = ctx.inputs
        contact_file = task.work_dir / "contact_info.csv"

        try:
            with contact_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            actual_names = [row.get("Name", "") for row in rows if row.get("Name")]

            missing_names = set(EXPECTED_NAMES) - set(actual_names)
            if missing_names:
                return EvaluationReason(value=0.0, reason=f"Missing names: {sorted(missing_names)}")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking data completeness: {e}")

        return 1.0

