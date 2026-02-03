"""DirectoriesExist evaluator for size_classification task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.size_classification.constants import REQUIRED_DIRS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.size_classification.task import SizeClassificationTask


@dataclass
class DirectoriesExist(Evaluator["SizeClassificationTask", AgentRunResult]):
    """Evaluator that checks all three required directories exist."""

    async def evaluate(self, ctx: EvaluatorContext[SizeClassificationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all three required directories exist."""
        task = ctx.inputs

        for dir_name in REQUIRED_DIRS:
            dir_path = task.work_dir / dir_name
            if not dir_path.exists():
                return EvaluationReason(value=0.0, reason=f"Directory '{dir_name}' not found")

            if not dir_path.is_dir():
                return EvaluationReason(value=0.0, reason=f"'{dir_name}' exists but is not a directory")

        return 1.0
