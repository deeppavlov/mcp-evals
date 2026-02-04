"""AlphabeticalOrder evaluator for file_merging task."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_merging.constants import EXPECTED_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_merging.task import FileMergingTask


class AlphabeticalOrder(Evaluator["FileMergingTask", AgentRunResult]):
    """Evaluator that checks files are in alphabetical order."""

    async def evaluate(self, ctx: EvaluatorContext[FileMergingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are in alphabetical order."""
        task = ctx.inputs
        merged_file = task.work_dir / "merged_content.txt"

        if not merged_file.exists():
            return EvaluationReason(value=0.0, reason="File 'merged_content.txt' not found")

        try:
            content = merged_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            # Extract filenames from the content (lines that contain .txt)
            found_files = []
            for line in lines:
                line_ = line.strip()
                # Check if this line contains any of the expected filenames
                for expected_file in EXPECTED_FILES:
                    if expected_file in line_:
                        found_files.append(expected_file)
                        break

            # Check if files are in alphabetical order
            if found_files != EXPECTED_FILES:
                msg = f"Files not in correct alphabetical order. Expected: {EXPECTED_FILES}, Found: {found_files}"
                return EvaluationReason(value=0.0, reason=msg)

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying alphabetical order: {e}")

        return 1.0
