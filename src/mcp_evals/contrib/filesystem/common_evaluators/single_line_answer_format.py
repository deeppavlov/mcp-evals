"""Common evaluators shared across filesystem tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class SingleLineAnswerFormat(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks answer file is a single non-empty line.

    Validates that a file contains exactly one non-empty line with optional
    additional checks for path format.

    Example:
        SingleLineAnswerFormat(
            file_path="answer.txt",
            must_be_relative_path=True,
            must_use_forward_slashes=True,
        )
        SingleLineAnswerFormat(
            file_path="answer.txt",
            must_contain="models/backbone_module.py",
        )
    """

    file_path: str = "answer.txt"
    must_be_relative_path: bool = False
    must_use_forward_slashes: bool = False
    must_contain: str | None = None

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

    def _validate_single_line(self, content: str) -> EvaluatorOutput | None:
        """Validate that content is a single line."""
        if not content:
            return EvaluationReason(value=0.0, reason="Answer file is empty")

        if len(content.split("\n")) > 1:
            return EvaluationReason(
                value=0.0,
                reason="Answer file contains multiple lines or additional text",
            )

        return None

    def _validate_path_format(self, content: str) -> EvaluatorOutput | None:
        """Validate path format if required."""
        if self.must_use_forward_slashes and "\\" in content:
            return EvaluationReason(
                value=0.0,
                reason="Answer uses backslashes instead of forward slashes",
            )

        if self.must_be_relative_path and (content.startswith("/") or ":" in content):
            return EvaluationReason(
                value=0.0,
                reason="Answer appears to be an absolute path",
            )

        return None

    def _validate_must_contain(self, content: str) -> EvaluatorOutput | None:
        """Validate that content contains required substring if specified."""
        if self.must_contain is not None and self.must_contain not in content:
            return EvaluationReason(
                value=0.0,
                reason=f"Answer should contain '{self.must_contain}'",
            )

        return None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Validate that the file has correct single-line answer format."""
        task = ctx.inputs
        file_path = task.work_dir / Path(self.file_path)

        error = self._check_file_exists(file_path)
        if error is not None:
            return error

        try:
            content = file_path.read_text(encoding="utf-8").strip()

            error = self._validate_single_line(content)
            if error is not None:
                return error

            error = self._validate_path_format(content)
            if error is not None:
                return error

            error = self._validate_must_contain(content)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading answer file: {e}",
            )

        return 1.0
