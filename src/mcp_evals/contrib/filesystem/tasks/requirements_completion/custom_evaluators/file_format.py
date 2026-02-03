"""FileFormat evaluator for requirements_completion task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.requirements_completion.task import RequirementsCompletionTask


@dataclass
class FileFormat(Evaluator["RequirementsCompletionTask", AgentRunResult]):
    """Evaluator that checks requirements.txt file has proper format."""

    async def evaluate(self, ctx: EvaluatorContext[RequirementsCompletionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the requirements.txt file has proper format."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")

            if not content.strip():
                return EvaluationReason(value=0.0, reason="File is completely empty")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file: {e}")

        return 1.0
