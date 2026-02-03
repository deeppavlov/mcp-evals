"""SongNamesMatchExpected evaluator for music_report task."""

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.music_report.constants import EXPECTED_SONGS


class SongNamesMatchExpected(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks all expected song names are present."""

    async def evaluate(self, ctx: EvaluatorContext["MusicReportTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all expected song names are present in the ranking."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            found_songs = []
            for i in range(20):
                if i >= len(lines):
                    break
                line = lines[i].strip()
                song_name = line.split(":", 1)[0].strip()
                found_songs.append(song_name)

            # Check if all expected songs are present
            missing_songs = [
                expected_song["song_name"]
                for expected_song in EXPECTED_SONGS
                if expected_song["song_name"] not in found_songs
            ]

            if missing_songs:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected songs: {missing_songs}",
                )

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking song names: {e}",
            )
        else:
            return 1.0

