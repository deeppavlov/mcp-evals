"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class FileContentStructure(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks file content structure (line count, format).

    Example:
        FileContentStructure("report.txt", expected_lines=25)
        FileContentStructure("data.csv", expected_lines=100, min_lines=50)
    """

    path: str
    expected_lines: int | None = None
    min_lines: int | None = None
    max_lines: int | None = None

    def _validate_file_path(self, file_path: Path) -> EvaluatorOutput | None:
        """Validate that the file path exists and is a file."""
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
        return None

    def _validate_line_count(self, line_count: int) -> EvaluatorOutput | None:
        """Validate line count against expected, min, and max constraints."""
        if self.expected_lines is not None and line_count != self.expected_lines:
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' has {line_count} lines, expected {self.expected_lines}",
            )
        if self.min_lines is not None and line_count < self.min_lines:
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' has {line_count} lines, expected at least {self.min_lines}",
            )
        if self.max_lines is not None and line_count > self.max_lines:
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' has {line_count} lines, expected at most {self.max_lines}",
            )
        return None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file has the expected line count.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs
        file_path = task.work_dir / self.path

        validation_error = self._validate_file_path(file_path)
        if validation_error is not None:
            return validation_error

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            line_count = len(lines)
        except PermissionError as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading file '{self.path}': {e}",
            )
        except UnicodeDecodeError as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error decoding file '{self.path}': {e}",
            )

        line_count_error = self._validate_line_count(line_count)
        if line_count_error is not None:
            return line_count_error

        return 1.0
