"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class DirectoryEmpty(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a directory is empty.

    Example:
        DirectoryEmpty("learning/progress_tracking")
        DirectoryEmpty("organized_projects/learning/progress_tracking")
    """

    path: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the directory at the specified path is empty.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs
        dir_path = task.work_dir / Path(self.path)

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
            files_in_dir = list(dir_path.iterdir())
            if files_in_dir:
                file_names = [f.name for f in files_in_dir]
                return EvaluationReason(
                    value=0.0,
                    reason=f"Directory '{self.path}' should be empty, but contains: {file_names}",
                )
        except (OSError, PermissionError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking directory '{self.path}': {e}",
            )

        return 1.0
