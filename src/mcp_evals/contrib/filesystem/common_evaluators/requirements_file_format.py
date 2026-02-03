"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class RequirementsFileFormat(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks requirements.txt file has proper format.

    Example:
        RequirementsFileFormat("requirements.txt")
        RequirementsFileFormat("requirements.txt", min_lines=3)
    """

    file_path: str
    min_lines: int | None = None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the requirements.txt file has proper format.

        The file path is resolved relative to the task's work directory.
        Checks that the file is not empty, and optionally has a minimum number of lines.
        """
        task = ctx.inputs
        requirements_file = task.work_dir / Path(self.file_path)

        if not requirements_file.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.file_path}' does not exist",
            )

        try:
            content = requirements_file.read_text(encoding="utf-8")

            if not content.strip():
                return EvaluationReason(
                    value=0.0,
                    reason="File is completely empty",
                )

            if self.min_lines is not None:
                lines = content.split("\n")
                non_empty_lines = [line.strip() for line in lines if line.strip()]
                if len(non_empty_lines) < self.min_lines:
                    return EvaluationReason(
                        value=0.0,
                        reason=(
                            f"File seems to have too few dependencies "
                            f"(found {len(non_empty_lines)}, expected at least {self.min_lines})"
                        ),
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking file: {e}",
            )

        return 1.0
