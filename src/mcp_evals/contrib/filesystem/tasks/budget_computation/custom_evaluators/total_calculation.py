"""TotalCalculation evaluator for budget_computation task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.budget_computation.constants import PRICE_TOLERANCE

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.budget_computation.task import BudgetComputationTask


@dataclass
class TotalCalculation(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks the total matches the sum of individual expenses."""

    async def evaluate(self, ctx: EvaluatorContext[BudgetComputationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the total matches the sum of individual expenses."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            expense_lines = lines[:-1]

            calculated_total = 0.0
            for line in expense_lines:
                price = float(line.split(";")[1])
                calculated_total += price

            stated_total = float(lines[-1])

            if abs(calculated_total - stated_total) > PRICE_TOLERANCE:
                msg = f"Total calculation mismatch: calculated {calculated_total:.2f}, stated {stated_total:.2f}"
                return EvaluationReason(value=0.0, reason=msg)

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying total calculation: {e}")

        return 1.0
