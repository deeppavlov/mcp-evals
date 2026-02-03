"""DirectoryStructure evaluator for time_classification task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.time_classification.constants import (
    DAY_MAPPING,
    EXPECTED_STRUCTURE,
    MONTH_MAPPING,
)
from mcp_evals.contrib.filesystem.tasks.time_classification.task import find_day_directory, find_month_directory

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.time_classification.task import TimeClassificationTask


@dataclass
class DirectoryStructure(Evaluator["TimeClassificationTask", AgentRunResult]):
    """Evaluator that checks correct directory structure exists."""

    async def evaluate(self, ctx: EvaluatorContext[TimeClassificationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the correct directory structure exists."""
        task = ctx.inputs

        for expected_month, days in EXPECTED_STRUCTURE.items():
            month_dir = find_month_directory(task.work_dir, expected_month)
            if month_dir is None:
                valid_names = MONTH_MAPPING.get(expected_month, [expected_month])
                return EvaluationReason(
                    value=0.0,
                    reason=f"Month directory not found. Expected one of: {valid_names}",
                )

            for day in days:
                day_dir = find_day_directory(month_dir, day)
                if day_dir is None:
                    valid_day_names = DAY_MAPPING.get(day, [day])
                    msg = f"Day directory '{month_dir.name}/{day}' not found. Expected one of: {valid_day_names}"
                    return EvaluationReason(value=0.0, reason=msg)

                if not day_dir.is_dir():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"'{month_dir.name}/{day_dir.name}' exists but is not a directory",
                    )

        return 1.0
