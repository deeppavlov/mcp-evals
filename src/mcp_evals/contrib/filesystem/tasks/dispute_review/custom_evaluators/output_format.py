"""OutputFormat evaluator for dispute_review task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.dispute_review.task import DisputeReviewTask


@dataclass
class OutputFormat(Evaluator["DisputeReviewTask", AgentRunResult]):
    """Evaluator that checks output file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext[DisputeReviewTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the output file has the correct format."""
        task = ctx.inputs
        output_file = task.work_dir / "dispute_review.txt"

        try:
            content = output_file.read_text(encoding="utf-8").strip()

            if not content:
                return EvaluationReason(value=0.0, reason="Output file is empty")

            lines = content.split("\n")
            for i, content_line in enumerate(lines, 1):
                stripped_line = content_line.strip()
                if not stripped_line:
                    continue

                # Check format: X.X:number
                if not re.match(r"^\d+\.\d+:\d+$", stripped_line):
                    reason_msg = (
                        f"Line {i} has incorrect format: '{stripped_line}'. "
                        f"Expected format: 'X.X:number' (e.g., '1.1:3')"
                    )
                    return EvaluationReason(value=0.0, reason=reason_msg)

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading output file: {e}")

        return 1.0
