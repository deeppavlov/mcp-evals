"""NoDuplicateEntries evaluator for requirements_writing task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.requirements_writing.task import RequirementsWritingTask


@dataclass
class NoDuplicateEntries(Evaluator["RequirementsWritingTask", AgentRunResult]):
    """Evaluator that checks there are no duplicate dependency entries."""

    async def evaluate(self, ctx: EvaluatorContext[RequirementsWritingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that there are no duplicate dependency entries."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")
            lines = [line.strip().lower() for line in content.split("\n") if line.strip()]

            if len(lines) != len(set(lines)):
                return EvaluationReason(
                    value=0.0,
                    reason="File contains duplicate entries",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking for duplicates: {e}")

        return 1.0
