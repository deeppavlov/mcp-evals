"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class NoDuplicateLines(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks there are no duplicate lines in a file.

    Example:
        NoDuplicateLines("requirements.txt")
        NoDuplicateLines("answer.txt")
    """

    file_path: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that there are no duplicate lines in the file.

        The file path is resolved relative to the task's work directory.
        Comparison is case-insensitive and ignores leading/trailing whitespace.
        """
        task = ctx.inputs
        file_path = task.work_dir / Path(self.file_path)

        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.file_path}' does not exist",
            )

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = [line.strip().lower() for line in content.split("\n") if line.strip()]

            if len(lines) != len(set(lines)):
                return EvaluationReason(
                    value=0.0,
                    reason="File contains duplicate entries",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking for duplicates: {e}",
            )

        return 1.0
