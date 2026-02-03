"""NoExtraFiles evaluator for file_splitting task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_splitting.constants import EXPECTED_SPLIT_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_splitting.task import FileSplittingTask


@dataclass
class NoExtraFiles(Evaluator["FileSplittingTask", AgentRunResult]):
    """Evaluator that checks no extra files exist in the split directory."""

    async def evaluate(self, ctx: EvaluatorContext[FileSplittingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that no extra files exist in the split directory."""
        task = ctx.inputs
        split_dir = task.work_dir / "split"

        if not split_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'split' not found")

        expected_files = set(EXPECTED_SPLIT_FILES)
        actual_files = {f.name for f in split_dir.iterdir() if f.is_file()}

        extra_files = actual_files - expected_files
        if extra_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Extra files found in split directory: {sorted(extra_files)}",
            )

        return 1.0
