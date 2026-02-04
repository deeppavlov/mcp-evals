"""SongRankingFormat evaluator for music_report task."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import ColonSeparatedLineFormat

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.music_report.task import MusicReportTask


def _validate_song_name(song_name: str, line_num: int) -> EvaluatorOutput | None:
    """Validate song name format."""
    if not song_name.strip():
        return EvaluationReason(
            value=0.0,
            reason=f"Line {line_num} has empty song name",
        )
    return None


def _validate_score(score_str: str, line_num: int) -> EvaluatorOutput | None:
    """Validate score format and range."""
    try:
        score = float(score_str.strip())
        if score < 0 or score > 5:  # noqa: PLR2004
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has invalid score range: {score}",
            )
    except ValueError:
        return EvaluationReason(
            value=0.0,
            reason=f"Line {line_num} has invalid score format: '{score_str}'",
        )
    return None


class SongRankingFormat(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks lines 1-20 have correct song:score format."""

    async def evaluate(self, ctx: EvaluatorContext[MusicReportTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that lines 1-20 contain songs with scores in correct format."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        # Use ColonSeparatedLineFormat for validation of lines 1-20
        format_evaluator = ColonSeparatedLineFormat(
            file_path="music/music_analysis_report.txt",
            left_validator=_validate_song_name,
            right_validator=_validate_score,
            line_range=(0, 20),  # Lines 1-20 (0-indexed: 0 to 20)
        )

        return await format_evaluator.evaluate(ctx)
