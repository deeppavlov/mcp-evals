"""OriginalFileRemoved evaluator for find_math_paper task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.find_math_paper.task import FindMathPaperTask


@dataclass
class OriginalFileRemoved(Evaluator["FindMathPaperTask", AgentRunResult]):
    """Evaluator that checks the original file (2407.01284.html) no longer exists."""

    async def evaluate(self, ctx: EvaluatorContext[FindMathPaperTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the original file (2407.01284.html) no longer exists."""
        task = ctx.inputs
        original_file = task.work_dir / "2407.01284.html"

        if original_file.exists():
            return EvaluationReason(
                value=0.0,
                reason="Original file 2407.01284.html still exists",
            )

        return 1.0
