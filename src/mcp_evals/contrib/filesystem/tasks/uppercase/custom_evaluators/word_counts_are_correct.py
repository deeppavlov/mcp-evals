"""WordCountsAreCorrect evaluator for uppercase task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.uppercase.constants import EXPECTED_COUNTS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.uppercase.task import UppercaseTask


@dataclass
class WordCountsAreCorrect(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks word counts in answer.txt are correct."""

    async def evaluate(self, ctx: EvaluatorContext[UppercaseTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the word counts in answer.txt are correct."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"
        answer_file = uppercase_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()
            lines = content.split("\n")

            # Create a set of expected file entries for easier checking
            expected_entries = set()
            for i in range(1, 11):
                filename = f"file_{i:02d}.txt"
                expected_count = EXPECTED_COUNTS[i - 1]
                if i == 6:  # Special case for file_06.txt: can be 21 or 22  # noqa: PLR2004
                    expected_entries.add(f"{filename}:21")
                    expected_entries.add(f"{filename}:22")
                else:
                    expected_entries.add(f"{filename}:{expected_count}")

            # Check each line in the answer file
            found_entries = set()
            for line in lines:
                line_ = line.strip()
                if line_ in expected_entries:
                    found_entries.add(line_)
                else:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Invalid entry: {line_}",
                    )

            # Check if we found all expected entries
            if len(found_entries) != 10:  # noqa: PLR2004
                missing = expected_entries - found_entries
                msg = f"Found {len(found_entries)} entries, expected 10"
                if missing:
                    msg += f". Missing entries: {sorted(missing)}"
                return EvaluationReason(value=0.0, reason=msg)

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying word counts: {e}")

        return 1.0
