"""UppercaseDirectoryExists evaluator for uppercase task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.uppercase.task import UppercaseTask


@dataclass
class UppercaseDirectoryExists(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks uppercase directory exists."""

    async def evaluate(self, ctx: EvaluatorContext[UppercaseTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the uppercase directory exists."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"

        if not uppercase_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'uppercase' not found")

        if not uppercase_dir.is_dir():
            return EvaluationReason(value=0.0, reason="'uppercase' exists but is not a directory")

        return 1.0
