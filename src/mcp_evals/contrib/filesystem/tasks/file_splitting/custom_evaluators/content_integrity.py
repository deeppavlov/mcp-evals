"""ContentIntegrity evaluator for file_splitting task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_splitting.constants import EXPECTED_SPLIT_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_splitting.task import FileSplittingTask


@dataclass
class ContentIntegrity(Evaluator["FileSplittingTask", AgentRunResult]):
    """Evaluator that checks concatenated split files equal the original file."""

    async def evaluate(self, ctx: EvaluatorContext[FileSplittingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that concatenated split files equal the original file."""
        task = ctx.inputs
        split_dir = task.work_dir / "split"
        original_file = task.work_dir / "large_file.txt"

        # Read original content
        try:
            original_content = original_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading original file: {e}",
            )

        # Concatenate all split files
        concatenated_content = ""
        for filename in EXPECTED_SPLIT_FILES:
            file_path = split_dir / filename

            try:
                content = file_path.read_text(encoding="utf-8")
                concatenated_content += content
            except (OSError, UnicodeDecodeError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error reading {filename}: {e}",
                )

        # Compare content
        if concatenated_content != original_content:
            msg = (
                f"Concatenated content does not match original file. "
                f"Original: {len(original_content)}, "
                f"Concatenated: {len(concatenated_content)}"
            )
            return EvaluationReason(value=0.0, reason=msg)

        return 1.0
