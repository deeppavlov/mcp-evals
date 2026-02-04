"""ExpenseEntries evaluator for budget_computation task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.budget_computation.constants import EXPECTED_EXPENSE_COUNT, EXPECTED_TOTAL_LINES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.budget_computation.task import BudgetComputationTask


@dataclass
class ExpenseEntries(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks all 15 required expense entries are present."""

    async def evaluate(self, ctx: EvaluatorContext[BudgetComputationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 15 required expense entries are present."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            if len(lines) != EXPECTED_TOTAL_LINES:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Expected {EXPECTED_TOTAL_LINES} lines "
                        f"({EXPECTED_EXPENSE_COUNT} expenses + 1 total), found {len(lines)}"
                    ),
                )

            expense_lines = lines[:-1]

            if len(expense_lines) != EXPECTED_EXPENSE_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=(f"Expected {EXPECTED_EXPENSE_COUNT} expense entries, found {len(expense_lines)}"),
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking expense entries: {e}")

        return 1.0
