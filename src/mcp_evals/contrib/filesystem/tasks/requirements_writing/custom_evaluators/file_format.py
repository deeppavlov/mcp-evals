"""FileFormat evaluator for requirements_writing task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.requirements_writing.task import RequirementsWritingTask


@dataclass
class FileFormat(Evaluator["RequirementsWritingTask", AgentRunResult]):
    """Evaluator that checks requirements.txt file has proper format."""

    async def evaluate(self, ctx: EvaluatorContext[RequirementsWritingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the requirements.txt file has proper format."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            if not content.strip():
                return EvaluationReason(value=0.0, reason="File is completely empty")

            non_empty_lines = [line.strip() for line in lines if line.strip()]
            if len(non_empty_lines) < 3:  # noqa: PLR2004
                return EvaluationReason(
                    value=0.0,
                    reason="File seems to have too few dependencies",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file: {e}")

        return 1.0
