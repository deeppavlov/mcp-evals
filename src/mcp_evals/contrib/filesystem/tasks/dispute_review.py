"""Dispute Review task for filesystem domain."""

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected entries based on answer.txt
EXPECTED_ENTRIES = {
    "1.1": 3,
    "1.3": 3,
    "4.6": [5, 6],  # Can be either 5 or 6
    "4.16": 5,
    "6.8": 4,
}


@dataclass
class OutputFormat(Evaluator["DisputeReviewTask", AgentRunResult]):
    """Evaluator that checks output file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext["DisputeReviewTask", AgentRunResult]) -> EvaluatorOutput:
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

    async def evaluate(self, ctx: EvaluatorContext["DisputeReviewTask", AgentRunResult]) -> EvaluatorOutput:
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


class DisputeReviewTask(FilesystemTask):
    """Task for reviewing legal document disputes and counting comments.

    The agent must:
    1. Review versions v5, v6, v7 in legal_files/
    2. Identify all clauses that have been commented
    3. Generate dispute_review.txt with format: Clause number:number of comments
    """

    name = "dispute_review"
    goal = """Please use FileSystem tools to finish the following task:

**Overview**

The folder "legal_files/" contains all versions
(Preferred_Stock_Purchase_Agreement_v0.txt -- Preferred_Stock_Purchase_Agreement_v10.txt)
of the Stock Purchase Agreement for a corporate investment project.

There are comments in it, come from four people:
- **Bill Harvey** (Company CEO)
- **Michelle Jackson** (Investor)
- **David Russel** (Company Counsel)
- **Tony Taylor** (Investor Counsel)

Between v1 and v9, these four people make comments on the clauses. The comment format is `[name:content]`, where:
- `name` is the commenter's name
- `content` is the revision note

**Special Note:** If the name is "All parties", it represents a joint comment from all parties,
which counts as one comment but does not count toward any individual's personal comment count.

## Task

Your task is to review these versions and identify all clauses that have been commented
in **v5,6,7 (in folder legal_files/)**. Generate a file named `dispute_review.txt` in the main directory.
In this file, list each commented clause on a separate line and indicate the number of comments
for each clause in the format "Clause number:number of comments".
Clause number should be in the format of X.X."""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("dispute_review.txt"),
            OutputFormat(),
            ExpectedEntries(),
        )
