"""FileFormat evaluator for budget_computation task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.budget_computation.constants import EXPECTED_PARTS, MIN_REQUIRED_ROWS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.budget_computation.task import BudgetComputationTask


@dataclass
class FileFormat(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks total_budget.txt file has proper format."""

    def _check_expense_line(self, line: str, line_num: int) -> EvaluatorOutput | None:
        """Check that an expense line has correct format."""
        if ";" not in line:
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} does not contain ';' separator: {line}",
            )

        parts = line.split(";")
        if len(parts) != EXPECTED_PARTS:
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} does not have exactly 2 parts: {line}",
            )

        try:
            float(parts[1])
        except ValueError:
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} price is not a valid number: {parts[1]}",
            )
        return None

    def _check_total_line(self, total_line: str) -> EvaluatorOutput | None:
        """Check that the total line is a valid number."""
        try:
            float(total_line)
        except ValueError:
            return EvaluationReason(
                value=0.0,
                reason=f"Last line is not a valid number: {total_line}",
            )
        return None

    async def evaluate(self, ctx: EvaluatorContext[BudgetComputationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the total_budget.txt file has proper format."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            if len(lines) < MIN_REQUIRED_ROWS:
                return EvaluationReason(
                    value=0.0,
                    reason="File must contain at least 2 lines (expenses + total)",
                )

            # Check that all lines except the last follow the format file_path;price
            for i, line in enumerate(lines[:-1]):
                expense_check = self._check_expense_line(line, i + 1)
                if expense_check is not None:
                    return expense_check

            # Check if last line is a valid number (total)
            total_check = self._check_total_line(lines[-1])
            if total_check is not None:
                return total_check

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading or parsing file: {e}")

        return 1.0
