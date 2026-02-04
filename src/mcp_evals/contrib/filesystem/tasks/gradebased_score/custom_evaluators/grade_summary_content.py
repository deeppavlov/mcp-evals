"""Evaluator that checks grade_summary.txt contains correct statistics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.gradebased_score.constants import EXPECTED_NUMBERS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.gradebased_score.task import GradebasedScoreTask


def extract_numbers_from_text(text: str) -> list[int]:
    """Extract all numbers from text."""
    numbers = re.findall(r"\d+", text)
    return [int(num) for num in numbers]


@dataclass
class GradeSummaryContent(Evaluator["GradebasedScoreTask", AgentRunResult]):
    """Evaluator that checks grade_summary.txt contains correct statistics."""

    async def evaluate(self, ctx: EvaluatorContext[GradebasedScoreTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that grade_summary.txt contains the correct statistics from answer.md."""
        task = ctx.inputs
        grade_summary_file = task.work_dir / "grade_summary.txt"

        try:
            content = grade_summary_file.read_text(encoding="utf-8")

            found_numbers = extract_numbers_from_text(content)

            if not found_numbers:
                return EvaluationReason(value=0.0, reason="No numbers found in grade_summary.txt")

            missing_numbers = [expected for expected in EXPECTED_NUMBERS if expected not in found_numbers]

            if missing_numbers:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected numbers: {missing_numbers}",
                )

            # Check if the counts match (each number should appear the expected number of times)
            for expected in EXPECTED_NUMBERS:
                expected_count = EXPECTED_NUMBERS.count(expected)
                found_count = found_numbers.count(expected)
                if found_count < expected_count:
                    return EvaluationReason(
                        value=0.0,
                        reason=(f"Number {expected} appears {found_count} times, expected {expected_count} times"),
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying grade summary content: {e}")

        return 1.0
