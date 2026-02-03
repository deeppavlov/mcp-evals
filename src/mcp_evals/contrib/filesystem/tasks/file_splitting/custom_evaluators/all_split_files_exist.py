"""AllSplitFilesExist evaluator for file_splitting task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_splitting.constants import EXPECTED_SPLIT_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_splitting.task import FileSplittingTask


@dataclass
class AllSplitFilesExist(Evaluator["FileSplittingTask", AgentRunResult]):
    """Evaluator that checks all 10 split files exist with correct names."""

    async def evaluate(self, ctx: EvaluatorContext[FileSplittingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 10 split files exist with correct names."""
        task = ctx.inputs
        split_dir = task.work_dir / "split"

        if not split_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'split' not found")

        missing_files = []
        for filename in EXPECTED_SPLIT_FILES:
            file_path = split_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing files: {missing_files}",
            )

        return 1.0
