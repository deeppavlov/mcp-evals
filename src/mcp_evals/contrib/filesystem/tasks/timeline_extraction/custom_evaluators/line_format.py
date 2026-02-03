"""LineFormat evaluator for timeline_extraction task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.timeline_extraction.utils import _has_path_like_content

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.timeline_extraction.task import TimelineExtractionTask


@dataclass
class LineFormat(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks each line contains both file path and date time information."""

    async def evaluate(self, ctx: EvaluatorContext[TimelineExtractionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that each line contains both file path and date time information."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            date_pattern = r"\d{4}-\d{2}-\d{2}"  # YYYY-MM-DD format

            invalid_lines = []
            for i, line in enumerate(lines, 1):
                # Check if line contains a date
                if not re.search(date_pattern, line):
                    invalid_lines.append(f"Line {i}: '{line}' (no valid date found)")
                    continue

                # Check if line contains path-like content
                if not _has_path_like_content(line):
                    invalid_lines.append(f"Line {i}: '{line}' (no valid path found)")

            if invalid_lines:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Invalid line format found: {invalid_lines[:5]}",
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking line format: {e}")

        return 1.0
