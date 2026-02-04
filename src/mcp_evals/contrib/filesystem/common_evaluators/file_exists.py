"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class FileExists(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a file exists.

    Example:
    - `FileExists("config.json")`
    - `FileExists("music/music_analysis_report.txt")`
    """

    path: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file at the specified path exists.

        The path is resolved relative to the current working directory
        or the filesystem root if set via environment variable.
        """
        task = ctx.inputs
        file_path = task.work_dir / Path(self.path)

        if file_path.exists() and file_path.is_file():
            return 1.0
        return EvaluationReason(
            value=0.0,
            reason=f"File '{self.path}' does not exist or is not a file",
        )
