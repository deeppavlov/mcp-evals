"""FilesInCorrectLocations evaluator for contact_information task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.contact_information.task import ContactInformationTask


@dataclass
class FilesInCorrectLocations(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks files are in correct locations."""

    async def evaluate(self, ctx: EvaluatorContext[ContactInformationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are in the correct locations."""
        task = ctx.inputs
        contact_file = task.work_dir / "contact_info.csv"
        answer_file = task.work_dir / "answer.txt"

        if contact_file.parent != task.work_dir:
            return EvaluationReason(
                value=0.0,
                reason=f"contact_info.csv is not in main directory: {contact_file}",
            )

        if answer_file.parent != task.work_dir:
            return EvaluationReason(
                value=0.0,
                reason=f"answer.txt is not in main directory: {answer_file}",
            )

        return 1.0
