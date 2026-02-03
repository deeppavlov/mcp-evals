"""CorrectFilesSelected evaluator for file_merging task."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_merging.constants import EXPECTED_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_merging.task import FileMergingTask


class CorrectFilesSelected(Evaluator["FileMergingTask", AgentRunResult]):
    """Evaluator that checks correct 10 files were selected and included."""

    async def evaluate(self, ctx: EvaluatorContext[FileMergingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the correct 10 files were selected and included."""
        task = ctx.inputs
        merged_file = task.work_dir / "merged_content.txt"

        if not merged_file.exists():
            return EvaluationReason(value=0.0, reason="File 'merged_content.txt' not found")

        try:
            content = merged_file.read_text(encoding="utf-8")

            # Check if all expected files are present
            for expected_file in EXPECTED_FILES:
                if expected_file not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Expected file '{expected_file}' not found in merged content",
                    )

            # Check if file_12.txt is NOT present (should be excluded)
            if "file_12.txt" in content:
                return EvaluationReason(
                    value=0.0,
                    reason="file_12.txt should be excluded but was found in merged content",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file selection: {e}")

        return 1.0
