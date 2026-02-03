"""ExpectedEntries evaluator for timeline_extraction task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.timeline_extraction.utils import (
    _check_extra_entries,
    _check_missing_entries,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.timeline_extraction.task import TimelineExtractionTask


@dataclass
class ExpectedEntries(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks all expected entries from answer.txt are present."""

    async def evaluate(self, ctx: EvaluatorContext[TimelineExtractionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all expected entries from answer.txt are present."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            actual_lines = [line.strip() for line in content.split("\n") if line.strip()]

            missing_entries = _check_missing_entries(actual_lines)
            if missing_entries:
                msg = f"Missing {len(missing_entries)} expected entries. Examples: {missing_entries[:3]}"
                return EvaluationReason(value=0.0, reason=msg)

            extra_entries = _check_extra_entries(actual_lines)
            if extra_entries:
                msg = f"Found {len(extra_entries)} unexpected entries. Examples: {extra_entries[:3]}"
                return EvaluationReason(value=0.0, reason=msg)
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking expected entries: {e}")

        return 1.0
