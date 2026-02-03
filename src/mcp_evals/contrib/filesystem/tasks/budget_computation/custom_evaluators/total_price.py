"""TotalPrice evaluator for budget_computation task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.budget_computation.constants import EXPECTED_TOTAL, PRICE_TOLERANCE

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.budget_computation.task import BudgetComputationTask


@dataclass
class TotalPrice(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks the total price is correct."""

    async def evaluate(self, ctx: EvaluatorContext[BudgetComputationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the total price is correct."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            total_line = lines[-1]
            try:
                actual_total = float(total_line)
            except ValueError:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Last line is not a valid number: {total_line}",
                )

            if abs(actual_total - EXPECTED_TOTAL) > PRICE_TOLERANCE:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Expected total {EXPECTED_TOTAL}, found {actual_total}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking total price: {e}")

        return 1.0
