"""Common evaluators shared across filesystem tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ColonSeparatedLineFormat(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that validates colon-separated line formats.

    Validates that lines in a file follow the format `left_part:right_part` with
    custom validators for each part.

    Example:
        ColonSeparatedLineFormat(
            file_path="answer.txt",
            left_validator=lambda left, line_num: validate_filename(left, line_num),
            right_validator=lambda right, line_num: validate_integer(right, line_num),
            expected_line_count=10,
        )
    """

    file_path: str
    left_validator: Callable[[str, int], EvaluatorOutput | None] | None = None
    right_validator: Callable[[str, int], EvaluatorOutput | None] | None = None
    expected_line_count: int | None = None
    line_range: tuple[int, int] | None = None
    allow_empty_lines: bool = False

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

    def _get_lines_to_validate(self, lines: list[str]) -> tuple[list[str], EvaluatorOutput | None]:
        """Get lines to validate based on line_range."""
        if self.line_range is not None:
            start_idx, end_idx = self.line_range
            # Check that file has enough lines
            if len(lines) < end_idx:
                missing_line_num = len(lines) + 1
                return [], EvaluationReason(
                    value=0.0,
                    reason=f"Line {missing_line_num} is missing",
                )
            return lines[start_idx:end_idx], None

        return lines, None

    def _check_line_count(self, lines_to_validate: list[str]) -> EvaluatorOutput | None:
        """Check expected line count if specified."""
        if self.expected_line_count is not None and len(lines_to_validate) != self.expected_line_count:
            return EvaluationReason(
                value=0.0,
                reason=(
                    f"File '{self.file_path}' has {len(lines_to_validate)} lines, expected {self.expected_line_count}"
                ),
            )
        return None

    def _validate_line_format(self, line_stripped: str, line_num: int) -> tuple[str, str, EvaluatorOutput | None]:
        """Validate colon-separated format and return parts or error."""
        # Check for colon separator
        if ":" not in line_stripped:
            return (
                "",
                "",
                EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Line {line_num} has incorrect format: '{line_stripped}'. "
                        f"Expected format: left_part:right_part"
                    ),
                ),
            )

        # Split by colon
        parts = line_stripped.split(":", 1)
        if len(parts) != 2:  # noqa: PLR2004
            return (
                "",
                "",
                EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Line {line_num} has incorrect format: '{line_stripped}'. "
                        f"Expected format: left_part:right_part"
                    ),
                ),
            )

        return parts[0], parts[1], None

    def _validate_line(self, line: str, line_num: int) -> EvaluatorOutput | None:
        """Validate a single line."""
        line_stripped = line.strip()

        # Handle empty lines
        if not line_stripped:
            if not self.allow_empty_lines:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Line {line_num} is empty",
                )
            return None

        # Validate format
        left_part, right_part, error = self._validate_line_format(line_stripped, line_num)
        if error is not None:
            return error

        # Validate left part if validator provided
        if self.left_validator is not None:
            error = self.left_validator(left_part, line_num)
            if error is not None:
                return error

        # Validate right part
        if self.right_validator is not None:
            error = self.right_validator(right_part, line_num)
            if error is not None:
                return error

        return None

    def _validate_all_lines(self, lines_to_validate: list[str], start_idx: int) -> EvaluatorOutput | None:
        """Validate all lines and return first error if any."""
        for i, line in enumerate(lines_to_validate):
            line_num = start_idx + i + 1
            error = self._validate_line(line, line_num)
            if error is not None:
                return error
        return None

    def _validate_file_content(self, file_path: Path) -> EvaluatorOutput:
        """Validate file content and return error or success."""
        try:
            content = file_path.read_text(encoding="utf-8").strip()

            if not content:
                return EvaluationReason(value=0.0, reason=f"File '{self.file_path}' is empty")

            lines = content.split("\n")

            # Get lines to validate
            lines_to_validate, error = self._get_lines_to_validate(lines)
            if error is not None:
                return error

            # Check line count
            error = self._check_line_count(lines_to_validate)
            if error is not None:
                return error

            # Determine start index for line numbering
            start_idx = self.line_range[0] if self.line_range is not None else 0

            # Validate all lines
            error = self._validate_all_lines(lines_to_validate, start_idx)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading file '{self.file_path}': {e}",
            )
        else:
            return 1.0

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Validate that the file has correct colon-separated line format."""
        task = ctx.inputs
        file_path = task.work_dir / Path(self.file_path)

        error = self._check_file_exists(file_path)
        if error is not None:
            return error

        return self._validate_file_content(file_path)
