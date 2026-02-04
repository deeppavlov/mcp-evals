"""AnswerFormat evaluator for uppercase task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import ColonSeparatedLineFormat

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.uppercase.task import UppercaseTask


def _validate_filename(filename: str, line_num: int) -> EvaluatorOutput | None:
    """Validate filename format."""
    if not filename.endswith(".txt") or not filename.startswith("file_"):
        return EvaluationReason(
            value=0.0,
            reason=f"Line {line_num} has invalid filename: '{filename}'",
        )
    return None


def _validate_word_count(word_count_str: str, line_num: int) -> EvaluatorOutput | None:
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


@dataclass
class AnswerFormat(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext[UppercaseTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer file has the correct format."""
        task = ctx.inputs
        answer_file = task.work_dir / "uppercase" / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        # Use ColonSeparatedLineFormat for validation
        format_evaluator = ColonSeparatedLineFormat(
            file_path="uppercase/answer.txt",
            left_validator=_validate_filename,
            right_validator=_validate_word_count,
            expected_line_count=10,
        )

        return await format_evaluator.evaluate(ctx)
