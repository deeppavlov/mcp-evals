"""AnswerFormat evaluator for uppercase task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.uppercase.task import UppercaseTask


@dataclass
class AnswerFormat(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    def _validate_word_count(self, word_count_str: str, line_num: int) -> EvaluatorOutput | None:
        """Validate word count format."""
        try:
            word_count = int(word_count_str)
            if word_count <= 0:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Line {line_num} has invalid word count: {word_count_str}",
                )
        except ValueError:
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has non-integer word count: '{word_count_str}'",
            )
        return None

    def _validate_line(self, line: str, line_num: int) -> EvaluatorOutput | None:
        """Validate a single line format."""
        if not line:
            return EvaluationReason(value=0.0, reason=f"Line {line_num} is empty")

        # Check format: filename:word_count
        if ":" not in line:
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has incorrect format: '{line}'. Expected format: filename:word_count",
            )

        parts = line.split(":", 1)
        if len(parts) != 2:  # noqa: PLR2004
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has incorrect format: '{line}'. Expected format: filename:word_count",
            )

        filename, word_count_str = parts

        # Check filename format
        if not filename.endswith(".txt") or not filename.startswith("file_"):
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has invalid filename: '{filename}'",
            )

        return self._validate_word_count(word_count_str, line_num)

    def _validate_all_lines(self, lines: list[str]) -> EvaluatorOutput | None:
        """Validate all lines in the answer file."""
        if len(lines) != 10:  # noqa: PLR2004
            return EvaluationReason(
                value=0.0,
                reason=f"Answer file has {len(lines)} lines, expected 10",
            )

        for i, line in enumerate(lines, 1):
            error = self._validate_line(line.strip(), i)
            if error is not None:
                return error
        return None

    async def evaluate(self, ctx: EvaluatorContext[UppercaseTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer file has the correct format."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"
        answer_file = uppercase_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            if not content:
                return EvaluationReason(value=0.0, reason="Answer file is empty")

            lines = content.split("\n")

            error = self._validate_all_lines(lines)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0
