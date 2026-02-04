"""Evaluator that checks file path contains the exact expected path string."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.output_analysis.constants import EXPECTED_FILE_PATH

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.output_analysis.task import OutputAnalysisTask


@dataclass
class FilePath(Evaluator["OutputAnalysisTask", AgentRunResult]):
    """Evaluator that checks file path contains the exact expected path string."""

    async def evaluate(self, ctx: EvaluatorContext[OutputAnalysisTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the file path contains the exact expected path string."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8")

            if EXPECTED_FILE_PATH not in content:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected file path: {EXPECTED_FILE_PATH}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file: {e}")

        return 1.0
