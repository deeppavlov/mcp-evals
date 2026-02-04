"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class DirectoryFileCounts(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks file counts in multiple directories.

    Example:
        DirectoryFileCounts({"dir1": 5, "dir2": 10})
        DirectoryFileCounts({"experiments/ml_projects": 6, "learning/resources": 7}, base_path="organized_projects")
    """

    counts: dict[str, int]
    base_path: str | None = None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if each directory contains the expected number of files.

        The directory paths are resolved relative to the task's work directory.
        If base_path is provided, directories are resolved relative to base_path.
        Only counts files, not subdirectories.
        """
        task = ctx.inputs

        base_dir = task.work_dir / Path(self.base_path) if self.base_path else task.work_dir

        incorrect_counts = []
        for dir_path, expected_count in self.counts.items():
            full_path = base_dir / dir_path
            try:
                if not full_path.exists():
                    incorrect_counts.append(f"{dir_path}: directory does not exist")
                    continue

                if not full_path.is_dir():
                    incorrect_counts.append(f"{dir_path}: not a directory")
                    continue

                actual_count = len([f for f in full_path.iterdir() if f.is_file()])

                if actual_count != expected_count:
                    incorrect_counts.append(
                        f"{dir_path}: expected {expected_count}, got {actual_count}",
                    )
            except (OSError, PermissionError) as e:
                incorrect_counts.append(f"{dir_path}: error reading directory - {e}")

        if incorrect_counts:
            return EvaluationReason(
                value=0.0,
                reason=f"Incorrect file counts: {incorrect_counts}",
            )

        return 1.0
