"""RequiredCategories evaluator for dataset_comparison task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.dataset_comparison.constants import REQUIRED_CATEGORIES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.dataset_comparison.task import DatasetComparisonTask


@dataclass
class RequiredCategories(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks all required SUN RGB-D categories are present."""

    async def evaluate(self, ctx: EvaluatorContext[DatasetComparisonTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required SUN RGB-D categories are present."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            categories_found = []
            line_index = 0

            while line_index < len(lines):
                while line_index < len(lines) and lines[line_index].strip() == "":
                    line_index += 1

                if line_index >= len(lines):
                    break

                category_line = lines[line_index].strip()
                if category_line:
                    categories_found.append(category_line.lower())

                line_index += 2
                while line_index < len(lines) and lines[line_index].strip() == "":
                    line_index += 1

            missing_categories = REQUIRED_CATEGORIES - set(categories_found)
            if missing_categories:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing required categories: {sorted(missing_categories)}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying required categories: {e}")

        return 1.0
