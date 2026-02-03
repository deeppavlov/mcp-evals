"""AnswerFormat evaluator for debugging task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.debugging.task import DebuggingTask


@dataclass
class AnswerFormat(Evaluator["DebuggingTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext[DebuggingTask, AgentRunResult]) -> EvaluatorOutput:
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

            if "models/backbone_module.py" not in content:
                return EvaluationReason(
                    value=0.0,
                    reason="Answer should contain 'models/backbone_module.py'",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0
