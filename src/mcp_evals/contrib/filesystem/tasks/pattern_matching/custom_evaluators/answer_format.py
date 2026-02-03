"""Evaluator that checks answer file has correct format."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.pattern_matching.task import PatternMatchingTask


@dataclass
class AnswerFormat(Evaluator["PatternMatchingTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    def _validate_line(self, line: str, line_num: int) -> EvaluatorOutput | None:
        """Validate a single line format."""
        parts = line.split(",")
        if len(parts) != 2:  # noqa: PLR2004
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has incorrect format '{line}'. Expected format: filename.txt,start_position",
            )

        filename, start_pos = parts

        # Check filename format
        if not filename.endswith(".txt") or not filename.startswith("file_"):
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has invalid filename: '{filename}'",
            )

        # Check position format (should be integer)
        try:
            start_int = int(start_pos)
            if start_int <= 0:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Line {line_num} has invalid position: {start_pos}",
                )
        except ValueError:
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has non-integer position: '{start_pos}'",
            )

        return None

    async def evaluate(self, ctx: EvaluatorContext[PatternMatchingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer file has the correct format."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            # If file is empty, that's acceptable (no matches found)
            if not content:
                return 1.0

            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                line_ = line.strip()
                if not line_:
                    continue

                error = self._validate_line(line_, i)
                if error is not None:
                    return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0
