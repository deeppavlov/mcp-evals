"""OthersFolderExists evaluator for file_arrangement task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_arrangement.task import FileArrangementTask


@dataclass
class OthersFolderExists(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks others folder exists and can contain any files."""

    async def evaluate(self, ctx: EvaluatorContext[FileArrangementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that others folder exists and can contain any files."""
        task = ctx.inputs
        others_dir = task.work_dir / "others"

        if not others_dir.exists() or not others_dir.is_dir():
            return EvaluationReason(value=0.0, reason="others/ folder not found")

        return 1.0
