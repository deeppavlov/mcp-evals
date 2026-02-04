"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class NoFilesInRoot(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks no files remain in the root directory.

    Example:
    - `NoFilesInRoot()`
    - `NoFilesInRoot([".DS_Store", "Thumbs.db"])`
    """

    system_files: list[str] | None = None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check that no files remain in the root directory.

        Optionally ignores system files like .DS_Store, Thumbs.db, etc.
        """
        task = ctx.inputs

        if self.system_files is None:
            system_files = [".DS_Store", "Thumbs.db", ".DS_Store?", "._.DS_Store"]
        else:
            system_files = self.system_files

        try:
            root_files = [f for f in task.work_dir.iterdir() if f.is_file()]
            non_system_files = [f for f in root_files if f.name not in system_files]

            if non_system_files:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Files still present in root directory: {[f.name for f in non_system_files]}",
                )
        except (OSError, PermissionError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading root directory: {e}",
            )

        return 1.0
