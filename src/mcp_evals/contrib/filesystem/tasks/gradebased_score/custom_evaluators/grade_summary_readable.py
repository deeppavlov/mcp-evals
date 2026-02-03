"""Evaluator that checks grade_summary.txt file is readable."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.gradebased_score.task import GradebasedScoreTask


@dataclass
class GradeSummaryReadable(Evaluator["GradebasedScoreTask", AgentRunResult]):
    """Evaluator that checks grade_summary.txt file is readable."""

    async def evaluate(self, ctx: EvaluatorContext[GradebasedScoreTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the grade_summary.txt file is readable."""
        task = ctx.inputs
        grade_summary_file = task.work_dir / "grade_summary.txt"

        try:
            content = grade_summary_file.read_text(encoding="utf-8")
            if not content.strip():
                return EvaluationReason(value=0.0, reason="grade_summary.txt file is empty")
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading grade_summary.txt file: {e}")

        return 1.0
