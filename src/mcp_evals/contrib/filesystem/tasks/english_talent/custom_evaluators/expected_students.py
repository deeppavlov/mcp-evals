"""ExpectedStudents evaluator for english_talent task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.english_talent.constants import EXPECTED_STUDENTS
from mcp_evals.contrib.filesystem.tasks.english_talent.task import parse_qualified_students_file

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.english_talent.task import EnglishTalentTask


@dataclass
class ExpectedStudents(Evaluator["EnglishTalentTask", AgentRunResult]):
    """Evaluator that checks all expected students are present with correct details."""

    async def evaluate(self, ctx: EvaluatorContext[EnglishTalentTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all expected students are present with correct details."""
        task = ctx.inputs

        students = parse_qualified_students_file(task.work_dir)

        if not students:
            return EvaluationReason(value=0.0, reason="Failed to parse qualified students file")

        found_students = {student["name"] for student in students}

        missing_students = set(EXPECTED_STUDENTS.keys()) - found_students
        if missing_students:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing expected students: {sorted(missing_students)}",
            )

        unexpected_students = found_students - set(EXPECTED_STUDENTS.keys())
        if unexpected_students:
            return EvaluationReason(
                value=0.0,
                reason=f"Unexpected students found: {sorted(unexpected_students)}",
            )

        for student in students:
            expected = EXPECTED_STUDENTS[student["name"]]
            if student["id"] != expected["id"]:
                return EvaluationReason(
                    value=0.0,
                    reason=(f"ID mismatch for {student['name']}: expected {expected['id']}, got {student['id']}"),
                )
            if student["email"] != expected["email"]:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Email mismatch for {student['name']}: expected {expected['email']}, got {student['email']}"
                    ),
                )

        return 1.0
