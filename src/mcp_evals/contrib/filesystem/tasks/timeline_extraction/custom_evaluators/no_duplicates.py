"""NoDuplicates evaluator for timeline_extraction task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.timeline_extraction.task import TimelineExtractionTask


@dataclass
class NoDuplicates(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks there are no duplicate entries."""

    async def evaluate(self, ctx: EvaluatorContext[TimelineExtractionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that there are no duplicate entries."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            if len(lines) != len(set(lines)):
                return EvaluationReason(value=0.0, reason="Duplicate entries found in timeline.txt")
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking for duplicates: {e}")

        return 1.0
