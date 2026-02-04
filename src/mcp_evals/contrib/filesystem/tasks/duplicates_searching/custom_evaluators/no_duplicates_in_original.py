"""NoDuplicatesInOriginal evaluator for duplicates_searching task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.duplicates_searching.constants import EXPECTED_DUPLICATE_GROUPS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.duplicates_searching.task import DuplicatesSearchingTask


@dataclass
class NoDuplicatesInOriginal(Evaluator["DuplicatesSearchingTask", AgentRunResult]):
    """Evaluator that checks no duplicate files remain in original location."""

    async def evaluate(self, ctx: EvaluatorContext[DuplicatesSearchingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that no duplicate files remain in the original location."""
        task = ctx.inputs

        remaining_duplicates = []
        for files in EXPECTED_DUPLICATE_GROUPS.values():
            for filename in files:
                file_path = task.work_dir / filename
                if file_path.exists():
                    remaining_duplicates.append(filename)

        if remaining_duplicates:
            return EvaluationReason(
                value=0.0,
                reason=f"Duplicate files still exist in original location: {remaining_duplicates}",
            )

        return 1.0
