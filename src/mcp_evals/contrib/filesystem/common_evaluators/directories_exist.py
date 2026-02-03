"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class DirectoriesExist(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if multiple directories exist.

    Example:
        DirectoriesExist(["dir1", "dir2", "dir3"])
        DirectoriesExist(["experiments", "learning"], base_path="organized_projects")
    """

    directories: list[str]
    base_path: str | None = None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if all specified directories exist.

        The directory paths are resolved relative to the task's work directory.
        If base_path is provided, directories are resolved relative to base_path.
        """
        task = ctx.inputs

        base_dir = task.work_dir / Path(self.base_path) if self.base_path else task.work_dir

        missing_dirs = []
        for dir_path in self.directories:
            full_path = base_dir / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
            elif not full_path.is_dir():
                missing_dirs.append(f"{dir_path} (not a directory)")

        if missing_dirs:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing or invalid directories: {missing_dirs}",
            )

        return 1.0
