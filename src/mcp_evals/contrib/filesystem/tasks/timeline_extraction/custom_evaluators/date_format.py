"""DateFormat evaluator for timeline_extraction task."""

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
class DateFormat(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks all dates are in valid YYYY-MM-DD format."""

    async def evaluate(self, ctx: EvaluatorContext[TimelineExtractionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all dates are in valid YYYY-MM-DD format."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            invalid_dates = []
            for i, line in enumerate(lines, 1):
                try:
                    date_match = re.search(r"\d{4}-\d{2}-\d{2}", line)
                    if not date_match:
                        invalid_dates.append(f"Line {i}: '{line}' (no date found)")
                        continue

                    date_part = date_match.group()
                    datetime.strptime(date_part, "%Y-%m-%d")  # noqa: DTZ007
                except (ValueError, IndexError) as e:
                    invalid_dates.append(f"Line {i}: '{line}' (invalid date: {e})")

            if invalid_dates:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Invalid date format found: {invalid_dates[:5]}",
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking date format: {e}")

        return 1.0
