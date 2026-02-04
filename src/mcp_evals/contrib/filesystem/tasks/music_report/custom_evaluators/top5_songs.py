"""Top5Songs evaluator for music_report task."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.music_report.constants import EXPECTED_TOP_5

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.music_report.task import MusicReportTask


class Top5Songs(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks lines 21-25 contain top 5 song names."""

    def _validate_top5_lines(self, lines: list[str]) -> tuple[list[str] | None, EvaluatorOutput | None]:
        """Validate top 5 lines format and return found songs or error."""
        found_top_5 = []
        for i in range(5):
            line_num = i + 21
            if i + 20 >= len(lines):
                return None, EvaluationReason(value=0.0, reason=f"Line {line_num} is missing")

            line = lines[i + 20].strip()

            if not line:
                return None, EvaluationReason(value=0.0, reason=f"Line {line_num} is empty")

            if ":" in line:
                return None, EvaluationReason(
                    value=0.0,
                    reason=f"Line {line_num} should not contain colon: '{line}'",
                )

            found_top_5.append(line)

        return found_top_5, None

    def _validate_top5_content(self, found_top_5: list[str]) -> EvaluatorOutput | None:
        """Validate top 5 songs content and order."""
        missing_songs = [expected_song for expected_song in EXPECTED_TOP_5 if expected_song not in found_top_5]

        if missing_songs:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing expected top 5 songs: {missing_songs}",
            )

        # Check if the order is valid (allowing equal scores to be swapped)
        valid_orders = [
            ["晴天", "七里香", "江南", "夜曲", "一千年以后"],  # Original order
            ["晴天", "江南", "七里香", "夜曲", "一千年以后"],  # Swapped 七里香 and 江南
        ]

        if found_top_5 not in valid_orders:
            msg = f"Top 5 songs order is invalid. Found: {found_top_5}, Expected one of: {valid_orders}"
            return EvaluationReason(value=0.0, reason=msg)

        return None

    async def evaluate(self, ctx: EvaluatorContext[MusicReportTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that lines 21-25 contain the top 5 song names."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            found_top_5, error = self._validate_top5_lines(lines)
            if error is not None:
                return error
            if found_top_5 is None:
                raise RuntimeError("Couldn't extract top 5 songs")

            error = self._validate_top5_content(found_top_5)
            if error is not None:
                return error

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking top 5 songs: {e}",
            )

        return 1.0
