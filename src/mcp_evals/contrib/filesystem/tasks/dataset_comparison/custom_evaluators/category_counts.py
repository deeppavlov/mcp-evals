"""CategoryCounts evaluator for dataset_comparison task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.dataset_comparison.constants import EXPECTED_COUNTS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.dataset_comparison.task import DatasetComparisonTask


@dataclass
class CategoryCounts(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks category counts match expected values."""

    def _parse_category_counts(self, lines: list[str]) -> dict[str, int]:
        """Parse category counts from lines."""
        category_counts = {}
        line_index = 0

        while line_index < len(lines):
            while line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1

            if line_index >= len(lines):
                break

            category_line = lines[line_index].strip()
            if not category_line:
                line_index += 1
                continue

            if line_index + 1 < len(lines):
                count_line = lines[line_index + 1].strip()
                if count_line:
                    count_match = re.search(r"(\d+)", count_line)
                    if count_match:
                        category = category_line.lower()
                        count = int(count_match.group(1))
                        category_counts[category] = count

            line_index += 2
            while line_index < len(lines) and lines[line_index].strip() == "":
                line_index += 1

        return category_counts

    def _validate_counts(self, category_counts: dict[str, int]) -> EvaluatorOutput | None:
        """Validate category counts match expected values."""
        for category, expected_count in EXPECTED_COUNTS.items():
            if category in category_counts:
                actual_count = category_counts[category]
                if actual_count != expected_count:
                    return EvaluationReason(
                        value=0.0,
                        reason=(f"Count mismatch for {category}: expected {expected_count}, got {actual_count}"),
                    )
            else:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Category {category} not found in analysis",
                )

        return None

    async def evaluate(self, ctx: EvaluatorContext[DatasetComparisonTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the category counts match the expected values."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            category_counts = self._parse_category_counts(lines)
            error = self._validate_counts(category_counts)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying category counts: {e}")

        return 1.0
