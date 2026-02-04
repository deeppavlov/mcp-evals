"""AnalysisFormat evaluator for dataset_comparison task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.dataset_comparison.task import DatasetComparisonTask


@dataclass
class AnalysisFormat(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks analysis file has correct format."""

    def _validate_block(self, lines: list[str], line_index: int) -> tuple[EvaluatorOutput | None, int]:
        """Validate a category block and return error or updated line_index."""
        if line_index + 1 >= len(lines):
            return EvaluationReason(value=0.0, reason="Incomplete category block at the end"), line_index

        category_line = lines[line_index].strip()
        if not category_line:
            return EvaluationReason(value=0.0, reason=f"Empty category name at line {line_index + 1}"), line_index

        count_line = lines[line_index + 1].strip()
        if not count_line:
            return EvaluationReason(value=0.0, reason=f"Empty count at line {line_index + 2}"), line_index

        if not re.search(r"\d+", count_line):
            return (
                EvaluationReason(
                    value=0.0,
                    reason=f"Count line doesn't contain a number at line {line_index + 2}: '{count_line}'",
                ),
                line_index,
            )

        line_index += 2
        if line_index < len(lines) and lines[line_index].strip() == "":
            line_index += 1

        return None, line_index

    def _validate_format(self, content: str, lines: list[str]) -> EvaluatorOutput | None:
        """Validate file format and return error if invalid."""
        if not content.strip():
            return EvaluationReason(value=0.0, reason="Analysis file is empty")

        if len(lines) < 2:  # noqa: PLR2004
            return EvaluationReason(
                value=0.0,
                reason="Analysis file doesn't have enough lines for a category block",
            )

        line_index = 0
        block_count = 0

        while line_index < len(lines):
            while line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1

            if line_index >= len(lines):
                break

            error, line_index = self._validate_block(lines, line_index)
            if error is not None:
                return error

            block_count += 1

        if block_count == 0:
            return EvaluationReason(value=0.0, reason="No valid category blocks found")

        return None

    async def evaluate(self, ctx: EvaluatorContext[DatasetComparisonTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the analysis file has the correct format."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            error = self._validate_format(content, lines)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading analysis file: {e}")

        return 1.0
