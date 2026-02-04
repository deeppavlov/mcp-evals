"""Evaluator that checks all matches are at least 30 characters long."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.pattern_matching.task import PatternMatchingTask


@dataclass
class MatchLengthIs30Plus(Evaluator["PatternMatchingTask", AgentRunResult]):
    """Evaluator that checks all matches are at least 30 characters long."""

    async def evaluate(self, ctx: EvaluatorContext[PatternMatchingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all matches are at least 30 characters long."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            if not content:
                return 1.0  # No matches to verify

            large_file = task.work_dir / "large_file.txt"
            large_content = large_file.read_text(encoding="utf-8")

            lines = content.split("\n")
            for line in lines:
                line_ = line.strip()
                if not line_:
                    continue

                filename, start_pos = line_.split(",")
                start_int = int(start_pos)

                # Get the file content to check the match
                file_path = task.work_dir / filename
                file_content = file_path.read_text(encoding="utf-8")

                # Find the longest matching substring starting from the given position
                longest_match = ""
                # At least 30 characters
                for end_pos in range(start_int + 30 - 1, len(large_content) + 1):
                    # Convert to 0-indexed
                    substring = large_content[start_int - 1 : end_pos]
                    if substring in file_content:
                        longest_match = substring
                    else:
                        break

                if len(longest_match) < 30:  # noqa: PLR2004
                    msg = f"Match in {filename} is {len(longest_match)} characters, less than 30"
                    return EvaluationReason(value=0.0, reason=msg)

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying match lengths: {e}")

        return 1.0
