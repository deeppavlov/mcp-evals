"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class DirectoryExists(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a directory exists.

    Example:
        DirectoryExists("duplicates")
        DirectoryExists("music/reports")
    """

    path: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the directory at the specified path exists.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs

        dir_path = task.work_dir / self.path

        if dir_path.exists() and dir_path.is_dir():
            return 1.0
        return EvaluationReason(
            value=0.0,
            reason=f"Directory '{self.path}' does not exist or is not a directory",
        )
