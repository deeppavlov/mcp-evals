"""FileFormat evaluator for english_talent task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.english_talent.task import EnglishTalentTask


@dataclass
class FileFormat(Evaluator["EnglishTalentTask", AgentRunResult]):
    """Evaluator that checks qualified_students.txt file has correct format."""

    def _validate_student_entry(self, lines: list[str], current_line: int) -> EvaluatorOutput | None:
        """Validate a single student entry."""
        if current_line + 2 >= len(lines):
            return EvaluationReason(
                value=0.0,
                reason=f"Incomplete student entry at line {current_line + 1}",
            )

        if not lines[current_line].strip().startswith("name: "):
            return EvaluationReason(
                value=0.0,
                reason=f"Invalid name line format at line {current_line + 1}: {lines[current_line]}",
            )

        if not lines[current_line + 1].strip().startswith("id: "):
            return EvaluationReason(
                value=0.0,
                reason=f"Invalid id line format at line {current_line + 2}: {lines[current_line + 1]}",
            )

        if not lines[current_line + 2].strip().startswith("email: "):
            return EvaluationReason(
                value=0.0,
                reason=f"Invalid email line format at line {current_line + 3}: {lines[current_line + 2]}",
            )

        return None

    def _validate_format(self, lines: list[str]) -> EvaluatorOutput | None:
        """Validate file format."""
        if not lines:
            return EvaluationReason(value=0.0, reason="File is empty")

        current_line = 0
        student_count = 0

        while current_line < len(lines):
            if not lines[current_line].strip():
                current_line += 1
                continue

            error = self._validate_student_entry(lines, current_line)
            if error is not None:
                return error

            student_count += 1
            current_line += 3

            if current_line < len(lines) and lines[current_line].strip():
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing blank line separator after student {student_count}",
                )

            current_line += 1

        if student_count == 0:
            return EvaluationReason(value=0.0, reason="No valid student entries found")

        return None

    async def evaluate(self, ctx: EvaluatorContext[EnglishTalentTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the qualified_students.txt file has the correct format."""
        task = ctx.inputs
        answer_file = task.work_dir / "qualified_students.txt"

        try:
            content = answer_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            error = self._validate_format(lines)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading qualified students file: {e}")

        return 1.0
