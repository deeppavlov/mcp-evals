"""ChronologicalOrder evaluator for timeline_extraction task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.timeline_extraction.task import TimelineExtractionTask


@dataclass
class ChronologicalOrder(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks dates are in chronological order."""

    async def evaluate(self, ctx: EvaluatorContext[TimelineExtractionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that dates are in chronological order."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            dates = []
            for line in lines:
                date_match = re.search(r"\d{4}-\d{2}-\d{2}", line)
                if date_match:
                    date_obj = datetime.strptime(date_match.group(), "%Y-%m-%d")  # noqa: DTZ007
                    dates.append(date_obj)

            # Check if dates are in ascending order
            for i in range(1, len(dates)):
                if dates[i] < dates[i - 1]:
                    date1 = dates[i - 1].strftime("%Y-%m-%d")
                    date2 = dates[i].strftime("%Y-%m-%d")
                    msg = f"Date order violation: {date1} comes after {date2}"
                    return EvaluationReason(value=0.0, reason=msg)
        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking chronological order: {e}")

        return 1.0
