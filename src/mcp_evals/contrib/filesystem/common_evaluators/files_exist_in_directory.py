"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class FilesExistInDirectory(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if specific files exist in a directory.

    Example:
        FilesExistInDirectory("experiments/ml_projects", ["file1.py", "file2.py"])
        FilesExistInDirectory("organized_projects/learning/resources", EXPECTED_LEARNING_FILES)
    """

    directory: str
    files: list[str]

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if all specified files exist in the directory.

        The directory path is resolved relative to the task's work directory.
        """
        task = ctx.inputs
        dir_path = task.work_dir / Path(self.directory)

        if not dir_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"Directory '{self.directory}' does not exist",
            )

        if not dir_path.is_dir():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.directory}' is not a directory",
            )

        missing_files = []
        for filename in self.files:
            file_path = dir_path / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing files in '{self.directory}': {missing_files}",
            )

        return 1.0
