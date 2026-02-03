"""AnswerFormat evaluator for code_locating task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.code_locating.task import CodeLocatingTask


@dataclass
class AnswerFormat(Evaluator["CodeLocatingTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext[CodeLocatingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer file has the correct format."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            if not content:
                return EvaluationReason(value=0.0, reason="Answer file is empty")

            if len(content.split("\n")) > 1:
                return EvaluationReason(
                    value=0.0,
                    reason="Answer file contains multiple lines or additional text",
                )

            if "\\" in content:
                return EvaluationReason(
                    value=0.0,
                    reason="Answer uses backslashes instead of forward slashes",
                )

            if content.startswith("/") or ":" in content:
                return EvaluationReason(
                    value=0.0,
                    reason="Answer appears to be an absolute path",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0
