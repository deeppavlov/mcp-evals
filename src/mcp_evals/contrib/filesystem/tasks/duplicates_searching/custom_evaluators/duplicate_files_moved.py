"""DuplicateFilesMoved evaluator for duplicates_searching task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.duplicates_searching.constants import EXPECTED_DUPLICATE_GROUPS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.duplicates_searching.task import DuplicatesSearchingTask


@dataclass
class DuplicateFilesMoved(Evaluator["DuplicatesSearchingTask", AgentRunResult]):
    """Evaluator that checks all duplicate files have been moved to duplicates directory."""

    async def evaluate(self, ctx: EvaluatorContext[DuplicatesSearchingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all duplicate files are in the duplicates directory."""
        task = ctx.inputs

        duplicates_dir = task.work_dir / "duplicates"

        if not duplicates_dir.exists():
            return EvaluationReason(value=0.0, reason="Duplicates directory does not exist")

        missing_files = []
        for files in EXPECTED_DUPLICATE_GROUPS.values():
            for filename in files:
                file_path = duplicates_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing duplicate files in 'duplicates' directory: {missing_files}",
            )

        return 1.0
