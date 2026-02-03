"""LineCount evaluator for timeline_extraction task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.timeline_extraction.constants import EXPECTED_LINE_COUNT

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.timeline_extraction.task import TimelineExtractionTask


@dataclass
class LineCount(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks timeline.txt file has exactly 43 lines."""

    async def evaluate(self, ctx: EvaluatorContext[TimelineExtractionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the timeline.txt file has exactly 43 lines."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            if len(lines) != EXPECTED_LINE_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Expected {EXPECTED_LINE_COUNT} lines, but found {len(lines)} lines",
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking line count: {e}")

        return 1.0
