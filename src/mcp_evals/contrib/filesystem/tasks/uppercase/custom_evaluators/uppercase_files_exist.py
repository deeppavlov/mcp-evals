"""UppercaseFilesExist evaluator for uppercase task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.uppercase.constants import EXPECTED_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.uppercase.task import UppercaseTask


@dataclass
class UppercaseFilesExist(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks all 10 uppercase files exist."""

    async def evaluate(self, ctx: EvaluatorContext[UppercaseTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 10 uppercase files exist."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"

        if not uppercase_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'uppercase' not found")

        for filename in EXPECTED_FILES:
            file_path = uppercase_dir / filename

            if not file_path.exists():
                return EvaluationReason(
                    value=0.0,
                    reason=f"File '{filename}' not found in uppercase directory",
                )

        return 1.0
