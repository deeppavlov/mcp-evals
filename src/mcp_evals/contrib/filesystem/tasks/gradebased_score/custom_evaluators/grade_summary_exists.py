"""Evaluator that checks grade_summary.txt file exists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.gradebased_score.task import GradebasedScoreTask


@dataclass
class GradeSummaryExists(Evaluator["GradebasedScoreTask", AgentRunResult]):
    """Evaluator that checks grade_summary.txt file exists."""

    async def evaluate(self, ctx: EvaluatorContext[GradebasedScoreTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that grade_summary.txt file exists."""
        task = ctx.inputs
        grade_summary_file = task.work_dir / "grade_summary.txt"

        if not grade_summary_file.exists():
            return EvaluationReason(value=0.0, reason="File 'grade_summary.txt' not found")

        return 1.0
