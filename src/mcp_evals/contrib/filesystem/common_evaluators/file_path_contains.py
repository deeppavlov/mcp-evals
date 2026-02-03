"""Common evaluators shared across filesystem tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class FilePathContains(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks file path contains required components.

    Validates that a file path (read from a file) contains all required
    path components as substrings.

    Example:
        FilePathContains(
            file_path="answer.txt",
            required_components=["threestudio", "models", "guidance", "zero123_guidance.py"],
        )
        FilePathContains(
            file_path="answer.txt",
            required_components=["models", "backbone_module.py"],
        )
    """

    required_components: list[str]
    file_path: str = "answer.txt"

    def _check_file_exists(self, file_path: Path) -> EvaluatorOutput | None:
        """Check if file exists and is a file."""
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

        return None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the file path contains all required components."""
        task = ctx.inputs
        answer_file = task.work_dir / Path(self.file_path)

        error = self._check_file_exists(answer_file)
        if error is not None:
            return error

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            for component in self.required_components:
                if component not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Path missing expected component: {component}",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error verifying file: {e}",
            )

        return 1.0
