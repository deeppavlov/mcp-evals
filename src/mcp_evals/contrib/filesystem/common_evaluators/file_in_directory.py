"""Common evaluators shared across filesystem tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class FileInDirectory(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks file is in a specific directory.

    Validates that a file exists in the expected directory. If expected_directory
    is None, checks that the file is in the root work directory.

    Example:
        FileInDirectory(
            file_path="analysis.txt",
            expected_directory=None,  # None means root/work_dir
        )
        FileInDirectory(
            file_path="contact_info.csv",
            expected_directory=None,
        )
    """

    file_path: str
    expected_directory: str | None = None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the file is in the correct directory."""
        task = ctx.inputs
        file_path = task.work_dir / Path(self.file_path)

        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.file_path}' does not exist",
            )

        if not file_path.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.file_path}' is not a file",
            )

        if self.expected_directory is None:
            expected_dir = task.work_dir
        else:
            expected_dir = task.work_dir / Path(self.expected_directory)

        if file_path.parent != expected_dir:
            if self.expected_directory is None:
                reason = f"File '{self.file_path}' should be in the test directory root"
            else:
                reason = f"File '{self.file_path}' is not in directory '{self.expected_directory}'"
            return EvaluationReason(
                value=0.0,
                reason=reason,
            )

        return 1.0
