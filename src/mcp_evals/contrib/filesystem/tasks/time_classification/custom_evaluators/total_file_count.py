"""TotalFileCount evaluator for time_classification task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.time_classification.constants import (
    EXPECTED_STRUCTURE,
    SYSTEM_FILES,
    TOTAL_EXPECTED_FILES,
)
from mcp_evals.contrib.filesystem.tasks.time_classification.task import (
    find_day_directory,
    find_month_directory,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.time_classification.task import TimeClassificationTask


@dataclass
class TotalFileCount(Evaluator["TimeClassificationTask", AgentRunResult]):
    """Evaluator that checks all original files are accounted for."""

    async def evaluate(self, ctx: EvaluatorContext[TimeClassificationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all original files are accounted for."""
        task = ctx.inputs

        total_actual = 0
        for expected_month, days in EXPECTED_STRUCTURE.items():
            month_dir = find_month_directory(task.work_dir, expected_month)
            if month_dir is None:
                continue

            for day in days:
                day_dir = find_day_directory(month_dir, day)
                if day_dir and day_dir.exists():
                    try:
                        files_in_dir = [f for f in day_dir.iterdir() if f.is_file() and f.name not in SYSTEM_FILES]
                        total_actual += len(files_in_dir)
                    except (OSError, PermissionError):
                        continue

        if total_actual != TOTAL_EXPECTED_FILES:
            return EvaluationReason(
                value=0.0,
                reason=f"Expected {TOTAL_EXPECTED_FILES} files total, found {total_actual}",
            )

        return 1.0
