"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class FileCount(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a directory contains the expected number of files.

    Example:
        FileCount("duplicates", expected=14)
        FileCount("music", expected=20)
    """

    path: str
    expected: int

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the directory contains the expected number of files.

        The path is resolved relative to the task's work directory.
        Only counts files, not subdirectories.
        """
        task = ctx.inputs

        dir_path = task.work_dir / self.path

        if not dir_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"Directory '{self.path}' does not exist",
            )

        if not dir_path.is_dir():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.path}' is not a directory",
            )

        try:
            file_count = sum(1 for item in dir_path.iterdir() if item.is_file())
            if file_count == self.expected:
                return 1.0
            return EvaluationReason(
                value=0.0,
                reason=f"Directory '{self.path}' contains {file_count} files, expected {self.expected}",
            )
        except PermissionError as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading directory '{self.path}': {e}",
            )
