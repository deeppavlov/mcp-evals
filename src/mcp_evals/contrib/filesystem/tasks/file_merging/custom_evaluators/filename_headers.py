"""FilenameHeaders evaluator for file_merging task."""

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_merging.constants import EXPECTED_FILES


class FilenameHeaders(Evaluator["FileMergingTask", AgentRunResult]):
    """Evaluator that checks each file section starts with correct filename header."""

    async def evaluate(self, ctx: EvaluatorContext["FileMergingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that each file section starts with the correct filename header."""
        task = ctx.inputs
        merged_file = task.work_dir / "merged_content.txt"

        if not merged_file.exists():
            return EvaluationReason(value=0.0, reason="File 'merged_content.txt' not found")

        try:
            content = merged_file.read_text(encoding="utf-8")

            for expected_file in EXPECTED_FILES:
                # Check if the filename appears anywhere in the content (as part of a line)
                if expected_file not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Filename header '{expected_file}' not found",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying filename headers: {e}")

        return 1.0

