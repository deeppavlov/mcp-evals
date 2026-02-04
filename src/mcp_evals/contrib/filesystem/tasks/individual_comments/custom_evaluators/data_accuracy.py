"""Evaluator that checks data values are accurate (all values are non-negative integers)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.individual_comments.constants import EXPECTED_COLUMN_COUNT

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.individual_comments.task import IndividualCommentsTask


@dataclass
class DataAccuracy(Evaluator["IndividualCommentsTask", AgentRunResult]):
    """Evaluator that checks data values are accurate (all values are non-negative integers)."""

    async def evaluate(self, ctx: EvaluatorContext[IndividualCommentsTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the data values are accurate (all values are non-negative integers)."""
        task = ctx.inputs
        output_file = task.work_dir / "individual_comment.csv"

        try:
            with output_file.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                # Skip header row
                for i, row in enumerate(rows[1:], 1):
                    if len(row) >= EXPECTED_COLUMN_COUNT:
                        # Check all clause columns (skip first column which is name)
                        for j, value in enumerate(row[1:EXPECTED_COLUMN_COUNT], 1):
                            try:
                                int_value = int(value)
                                if int_value < 0:
                                    return EvaluationReason(
                                        value=0.0,
                                        reason=f"Row {i}, column {j} has negative value: {value}",
                                    )
                            except ValueError:
                                return EvaluationReason(
                                    value=0.0,
                                    reason=f"Row {i}, column {j} has non-integer value: {value}",
                                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking data accuracy: {e}")

        return 1.0
