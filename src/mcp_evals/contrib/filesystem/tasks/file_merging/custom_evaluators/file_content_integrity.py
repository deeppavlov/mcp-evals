"""FileContentIntegrity evaluator for file_merging task."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_merging.constants import EXPECTED_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_merging.task import FileMergingTask


class FileContentIntegrity(Evaluator["FileMergingTask", AgentRunResult]):
    """Evaluator that checks content of each file is preserved correctly."""

    def _find_header_index(self, lines: list[str], expected_file: str) -> int:
        """Find the line index where the file header appears."""
        for i, line in enumerate(lines):
            if expected_file in line:
                return i
        return -1

    def _find_next_header_index(self, lines: list[str], start_index: int, current_file: str) -> int:
        """Find the next header line index."""
        for i in range(start_index + 1, len(lines)):
            for other_file in EXPECTED_FILES:
                if other_file != current_file and other_file in lines[i]:
                    return i
        return len(lines)

    def _validate_file_content(
        self, task: FileMergingTask, lines: list[str], expected_file: str
    ) -> EvaluatorOutput | None:
        """Validate content for a single file."""
        original_file = task.work_dir / expected_file
        if not original_file.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"Original file '{expected_file}' not found",
            )

        original_content = original_file.read_text(encoding="utf-8").strip()

        header_line_index = self._find_header_index(lines, expected_file)
        if header_line_index == -1:
            return EvaluationReason(
                value=0.0,
                reason=f"Could not find header for {expected_file}",
            )

        next_header_index = self._find_next_header_index(lines, header_line_index, expected_file)
        content_lines = lines[header_line_index + 1 : next_header_index]
        merged_content = "\n".join(content_lines).strip()

        if merged_content != original_content:
            return EvaluationReason(
                value=0.0,
                reason=f"Content mismatch for {expected_file}",
            )

        return None

    async def evaluate(self, ctx: EvaluatorContext[FileMergingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the content of each file is preserved correctly."""
        task = ctx.inputs
        merged_file = task.work_dir / "merged_content.txt"

        if not merged_file.exists():
            return EvaluationReason(value=0.0, reason="File 'merged_content.txt' not found")

        try:
            content = merged_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            for expected_file in EXPECTED_FILES:
                error = self._validate_file_content(task, lines, expected_file)
                if error is not None:
                    return error

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying content integrity: {e}")

        return 1.0

