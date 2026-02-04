"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class FileReadable(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a file exists and is readable/not empty.

    Example:
    - `FileReadable("timeline.txt")`
    - `FileReadable("structure_analysis.txt")`
    """

    path: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file at the specified path exists and is readable/not empty.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs
        file_path = task.work_dir / Path(self.path)

        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' does not exist",
            )

        if not file_path.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.path}' is not a file",
            )

        try:
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                return EvaluationReason(
                    value=0.0,
                    reason=f"File '{self.path}' is empty",
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading file '{self.path}': {e}",
            )

        return 1.0
