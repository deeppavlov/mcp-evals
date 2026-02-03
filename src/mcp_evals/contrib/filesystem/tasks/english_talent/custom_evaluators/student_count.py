"""StudentCount evaluator for english_talent task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.english_talent.constants import EXPECTED_STUDENT_COUNT
from mcp_evals.contrib.filesystem.tasks.english_talent.task import parse_qualified_students_file

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.english_talent.task import EnglishTalentTask


@dataclass
class StudentCount(Evaluator["EnglishTalentTask", AgentRunResult]):
    """Evaluator that checks exactly 19 students are found."""

    async def evaluate(self, ctx: EvaluatorContext[EnglishTalentTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that exactly 19 students are found."""
        task = ctx.inputs

        students = parse_qualified_students_file(task.work_dir)

        if not students:
            return EvaluationReason(value=0.0, reason="Failed to parse qualified students file")

        if len(students) != EXPECTED_STUDENT_COUNT:
            return EvaluationReason(
                value=0.0,
                reason=f"Expected {EXPECTED_STUDENT_COUNT} students, but found {len(students)}",
            )

        return 1.0
