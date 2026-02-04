"""UniqueFilesRemain evaluator for duplicates_searching task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.duplicates_searching.constants import EXPECTED_UNIQUE_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.duplicates_searching.task import DuplicatesSearchingTask


@dataclass
class UniqueFilesRemain(Evaluator["DuplicatesSearchingTask", AgentRunResult]):
    """Evaluator that checks unique files remain in original location."""

    async def evaluate(self, ctx: EvaluatorContext[DuplicatesSearchingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that unique files remain in the original location."""
        task = ctx.inputs

        missing_files = []
        for filename in EXPECTED_UNIQUE_FILES:
            file_path = task.work_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing unique files in original location: {missing_files}",
            )

        return 1.0
