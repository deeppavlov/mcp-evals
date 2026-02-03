"""TotalFileCount evaluator for size_classification task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.size_classification.constants import (
    REQUIRED_DIRS,
    SYSTEM_FILES,
    TOTAL_EXPECTED_FILES,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.size_classification.task import SizeClassificationTask


@dataclass
class TotalFileCount(Evaluator["SizeClassificationTask", AgentRunResult]):
    """Evaluator that checks all original files are accounted for."""

    async def evaluate(self, ctx: EvaluatorContext[SizeClassificationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all original files are accounted for."""
        task = ctx.inputs

        total_actual = 0
        for dir_name in REQUIRED_DIRS:
            dir_path = task.work_dir / dir_name
            if dir_path.exists():
                try:
                    files_in_dir = [f for f in dir_path.iterdir() if f.is_file() and f.name not in SYSTEM_FILES]
                    total_actual += len(files_in_dir)
                except (OSError, PermissionError):
                    continue

        if total_actual != TOTAL_EXPECTED_FILES:
            return EvaluationReason(
                value=0.0,
                reason=f"Expected {TOTAL_EXPECTED_FILES} files total, found {total_actual}",
            )

        return 1.0
