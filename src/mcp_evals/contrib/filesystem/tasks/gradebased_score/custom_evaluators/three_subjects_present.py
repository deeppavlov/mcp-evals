"""Evaluator that checks grade_summary.txt contains all three subjects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.gradebased_score.task import GradebasedScoreTask


@dataclass
class ThreeSubjectsPresent(Evaluator["GradebasedScoreTask", AgentRunResult]):
    """Evaluator that checks grade_summary.txt contains all three subjects."""

    async def evaluate(self, ctx: EvaluatorContext[GradebasedScoreTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that grade_summary.txt contains all three subjects (case insensitive)."""
        task = ctx.inputs
        grade_summary_file = task.work_dir / "grade_summary.txt"

        try:
            content = grade_summary_file.read_text(encoding="utf-8")

            subjects = ["chinese", "math", "english"]
            missing_subjects = [subject for subject in subjects if subject.lower() not in content.lower()]

            if missing_subjects:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing subjects in grade_summary.txt: {missing_subjects}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking subjects: {e}")

        return 1.0
