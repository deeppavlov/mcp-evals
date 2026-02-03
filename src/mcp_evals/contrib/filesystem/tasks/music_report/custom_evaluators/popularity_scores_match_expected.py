"""PopularityScoresMatchExpected evaluator for music_report task."""

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.music_report.constants import EXPECTED_SONGS


class PopularityScoresMatchExpected(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks popularity scores match expected values."""

    async def evaluate(self, ctx: EvaluatorContext["MusicReportTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that popularity scores match the expected values."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            score_errors = []
            for i in range(20):
                if i >= len(lines):
                    break

                line = lines[i].strip()
                parts = line.split(":", 1)
                song_name = parts[0].strip()
                actual_score = float(parts[1].strip())

                # Find expected score for this song
                expected_score: float | None = None
                for expected_song in EXPECTED_SONGS:
                    if expected_song["song_name"] == song_name:
                        score_value = expected_song["popularity_score"]
                        expected_score = float(score_value) if isinstance(score_value, (int, float, str)) else None
                        break

                if expected_score is not None and abs(actual_score - expected_score) > 0.001:  # noqa: PLR2004
                    msg = f"{song_name}: expected {expected_score}, got {actual_score}"
                    score_errors.append(msg)

            if score_errors:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Score mismatches: {score_errors}",
                )

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking popularity scores: {e}",
            )
        else:
            return 1.0

