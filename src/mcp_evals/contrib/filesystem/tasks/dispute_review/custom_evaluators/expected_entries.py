"""ExpectedEntries evaluator for dispute_review task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.dispute_review.constants import EXPECTED_ENTRIES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.dispute_review.task import DisputeReviewTask


@dataclass
class ExpectedEntries(Evaluator["DisputeReviewTask", AgentRunResult]):
    """Evaluator that checks output contains expected entries with correct counts."""

    def _check_entry_counts(self, output_entries: dict[str, int]) -> EvaluatorOutput | None:
        """Check that entry counts match expected values."""
        for clause, expected_count in EXPECTED_ENTRIES.items():
            actual_count = output_entries[clause]

            if isinstance(expected_count, list):
                # For 4.6, accept either 5 or 6
                if actual_count not in expected_count:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Clause {clause}: expected {expected_count}, got {actual_count}",
                    )
            elif actual_count != expected_count:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Clause {clause}: expected {expected_count}, got {actual_count}",
                )
        return None

    async def evaluate(self, ctx: EvaluatorContext[DisputeReviewTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the output contains the expected entries with correct counts."""
        task = ctx.inputs
        output_file = task.work_dir / "dispute_review.txt"

        try:
            content = output_file.read_text(encoding="utf-8").strip()
            lines = content.split("\n")

            # Parse the output into a dictionary
            output_entries: dict[str, int] = {}
            for content_line in lines:
                stripped_line = content_line.strip()
                if not stripped_line:
                    continue
                clause, count_str = stripped_line.split(":", 1)
                output_entries[clause] = int(count_str)

            # Check if all expected entries are present
            missing_entries = [clause for clause in EXPECTED_ENTRIES if clause not in output_entries]

            if missing_entries:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected entries: {missing_entries}",
                )

            # Check if there are extra entries
            extra_entries = [clause for clause in output_entries if clause not in EXPECTED_ENTRIES]

            if extra_entries:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Unexpected extra entries: {extra_entries}",
                )

            # Check counts for each entry
            count_check = self._check_entry_counts(output_entries)
            if count_check is not None:
                return count_check

        except (OSError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying entries: {e}")

        return 1.0
