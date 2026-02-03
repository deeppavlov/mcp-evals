"""Evaluator that checks line numbers contain (323 or 324) AND (327 or 328)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.output_analysis.task import OutputAnalysisTask


@dataclass
class LineNumbers(Evaluator["OutputAnalysisTask", AgentRunResult]):
    """Evaluator that checks line numbers contain (323 or 324) AND (327 or 328)."""

    async def evaluate(self, ctx: EvaluatorContext[OutputAnalysisTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that line numbers contain (323 or 324) AND (327 or 328)."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8")

            has_first = "323" in content or "324" in content
            has_second = "327" in content or "328" in content

            if not has_first:
                return EvaluationReason(
                    value=0.0,
                    reason="Missing first line number (323 or 324)",
                )

            if not has_second:
                return EvaluationReason(
                    value=0.0,
                    reason="Missing second line number (327 or 328)",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying line numbers: {e}")

        return 1.0
