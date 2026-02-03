"""IndividualPrices evaluator for budget_computation task."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.budget_computation.constants import EXPECTED_EXPENSES, PRICE_TOLERANCE
from mcp_evals.contrib.filesystem.tasks.budget_computation.task import path_matches_expected

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.budget_computation.task import BudgetComputationTask


@dataclass
class IndividualPrices(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks all individual prices match the expected values."""

    def _check_expected_expenses(
        self,
        expected_expenses_counter: Counter[tuple[str, float]],
        actual_expenses_counter: Counter[tuple[str, float]],
    ) -> EvaluatorOutput | None:
        """Check that all expected expenses are present with correct counts."""
        for expected_expense, expected_count in expected_expenses_counter.items():
            expected_path, expected_price = expected_expense

            matching_expenses = [
                actual_expense
                for actual_expense in actual_expenses_counter
                if path_matches_expected(actual_expense[0], expected_path)
                and abs(actual_expense[1] - expected_price) < PRICE_TOLERANCE
            ]

            if not matching_expenses:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected expense: {expected_expense}",
                )

            total_count = sum(actual_expenses_counter[expense] for expense in matching_expenses)
            if total_count != expected_count:
                msg = f"Expense {expected_expense} has wrong count: expected {expected_count}, found {total_count}"
                return EvaluationReason(value=0.0, reason=msg)
        return None

    def _check_unexpected_expenses(
        self,
        expected_expenses_counter: Counter[tuple[str, float]],
        actual_expenses_counter: Counter[tuple[str, float]],
    ) -> EvaluatorOutput | None:
        """Check for unexpected expenses."""
        all_matching_expenses = set()
        for expected_expense in expected_expenses_counter:
            expected_path, expected_price = expected_expense
            for actual_expense in actual_expenses_counter:
                actual_path, actual_price = actual_expense
                if (
                    path_matches_expected(actual_path, expected_path)
                    and abs(actual_price - expected_price) < PRICE_TOLERANCE
                ):
                    all_matching_expenses.add(actual_expense)

        unexpected_expenses = set(actual_expenses_counter) - all_matching_expenses
        if unexpected_expenses:
            return EvaluationReason(
                value=0.0,
                reason=f"Unexpected expenses found: {sorted(unexpected_expenses)}",
            )
        return None

    async def evaluate(self, ctx: EvaluatorContext[BudgetComputationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all individual prices match the expected values."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            expense_lines = lines[:-1]

            # Parse actual expenses
            actual_expenses = [(line.split(";")[0], float(line.split(";")[1])) for line in expense_lines]

            # Create counters for expected and actual expenses
            expected_expenses_counter = Counter(EXPECTED_EXPENSES)
            actual_expenses_counter = Counter(actual_expenses)

            # Check if all expected expenses are present with correct counts
            expected_check = self._check_expected_expenses(expected_expenses_counter, actual_expenses_counter)
            if expected_check is not None:
                return expected_check

            # Check if there are any completely unexpected expenses
            unexpected_check = self._check_unexpected_expenses(expected_expenses_counter, actual_expenses_counter)
            if unexpected_check is not None:
                return unexpected_check

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking individual prices: {e}")

        return 1.0
