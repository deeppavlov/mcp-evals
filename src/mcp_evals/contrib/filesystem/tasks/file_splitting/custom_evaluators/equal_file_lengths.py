"""EqualFileLengths evaluator for file_splitting task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_splitting.constants import EXPECTED_SPLIT_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_splitting.task import FileSplittingTask


@dataclass
class EqualFileLengths(Evaluator["FileSplittingTask", AgentRunResult]):
    """Evaluator that checks all split files have equal character counts."""

    async def evaluate(self, ctx: EvaluatorContext[FileSplittingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all split files have equal character counts."""
        task = ctx.inputs
        split_dir = task.work_dir / "split"

        if not split_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'split' not found")

        file_lengths = []
        for filename in EXPECTED_SPLIT_FILES:
            file_path = split_dir / filename

            try:
                content = file_path.read_text(encoding="utf-8")
                file_lengths.append(len(content))
            except (OSError, UnicodeDecodeError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error reading {filename}: {e}",
                )

        # Check if all lengths are equal
        if len(set(file_lengths)) != 1:
            return EvaluationReason(
                value=0.0,
                reason=f"File lengths are not equal: {file_lengths}",
            )

        return 1.0
