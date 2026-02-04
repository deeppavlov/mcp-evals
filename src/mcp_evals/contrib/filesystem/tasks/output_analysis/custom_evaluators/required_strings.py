"""Evaluator that checks answer contains the four required strings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.output_analysis.constants import REQUIRED_STRINGS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.output_analysis.task import OutputAnalysisTask


@dataclass
class RequiredStrings(Evaluator["OutputAnalysisTask", AgentRunResult]):
    """Evaluator that checks answer contains the four required strings."""

    async def evaluate(self, ctx: EvaluatorContext[OutputAnalysisTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer contains the four required strings."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8")

            missing_strings = [s for s in REQUIRED_STRINGS if s not in content]
            if missing_strings:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing required strings: {missing_strings}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0
