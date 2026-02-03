"""Evaluator that checks matches found in answer.txt are actually correct."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.pattern_matching.utils import find_30_plus_char_matches

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.pattern_matching.task import PatternMatchingTask


@dataclass
class MatchesAreCorrect(Evaluator["PatternMatchingTask", AgentRunResult]):
    """Evaluator that checks matches found in answer.txt are actually correct."""

    def _parse_answer_matches(self, content: str) -> dict[str, int]:
        """Parse answer matches from content."""
        answer_matches: dict[str, int] = {}
        lines = content.split("\n")
        for line in lines:
            line_ = line.strip()
            if not line_:
                continue
            filename, start_pos = line_.split(",")
            answer_matches[filename] = int(start_pos)
        return answer_matches

    def _validate_matches(
        self, answer_matches: dict[str, int], expected_matches: dict[str, int]
    ) -> EvaluatorOutput | None:
        """Validate that answer matches match expected matches."""
        # Check if all answer matches are correct
        for filename, start_pos in answer_matches.items():
            if filename not in expected_matches:
                msg = f"File {filename} listed in answer but has no valid 30+ character match"
                return EvaluationReason(value=0.0, reason=msg)

            expected_start = expected_matches[filename]
            if start_pos != expected_start:
                msg = f"Incorrect match position for {filename}. Expected: {expected_start}, Found: {start_pos}"
                return EvaluationReason(value=0.0, reason=msg)

        # Check if all expected matches are in answer
        for filename in expected_matches:
            if filename not in answer_matches:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing match for {filename} in answer file",
                )

        return None

    async def evaluate(self, ctx: EvaluatorContext[PatternMatchingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the matches found in answer.txt are actually correct."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            # If no content, check if there should actually be no matches
            if not content:
                expected_matches = find_30_plus_char_matches(task.work_dir)
                if expected_matches:
                    msg = f"Answer file is empty but matches should exist: {list(expected_matches.keys())}"
                    return EvaluationReason(value=0.0, reason=msg)
                return 1.0

            answer_matches = self._parse_answer_matches(content)
            expected_matches = find_30_plus_char_matches(task.work_dir)

            error = self._validate_matches(answer_matches, expected_matches)
            if error is not None:
                return error

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying matches: {e}")

        return 1.0
