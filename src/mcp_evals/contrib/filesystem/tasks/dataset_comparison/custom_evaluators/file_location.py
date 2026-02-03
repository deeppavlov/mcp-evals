"""FileLocation evaluator for dataset_comparison task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.dataset_comparison.task import DatasetComparisonTask


@dataclass
class FileLocation(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks analysis.txt file is in correct location."""

    async def evaluate(self, ctx: EvaluatorContext[DatasetComparisonTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the analysis.txt file is in the correct location."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        if analysis_file.parent != task.work_dir:
            return EvaluationReason(
                value=0.0,
                reason="Analysis file should be in the test directory root",
            )

        return 1.0
