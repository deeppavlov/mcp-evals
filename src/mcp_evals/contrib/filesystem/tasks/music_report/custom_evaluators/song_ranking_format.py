"""SongRankingFormat evaluator for music_report task."""

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput


class SongRankingFormat(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks lines 1-20 have correct song:score format."""

    def _validate_score(self, score_str: str, line_num: int) -> EvaluatorOutput | None:
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

    def _validate_line(self, line: str, line_num: int) -> EvaluatorOutput | None:
        """Validate a single line format."""
        if not line:
            return EvaluationReason(value=0.0, reason=f"Line {line_num} is empty")

        if ":" not in line:
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} missing colon separator: '{line}'",
            )

        parts = line.split(":", 1)
        if len(parts) != 2:  # noqa: PLR2004
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has incorrect format: '{line}'",
            )

        song_name, score_str = parts

        if not song_name.strip():
            return EvaluationReason(
                value=0.0,
                reason=f"Line {line_num} has empty song name: '{line}'",
            )

        return self._validate_score(score_str, line_num)

    def _validate_all_lines(self, lines: list[str]) -> EvaluatorOutput | None:
        """Validate all lines 1-20."""
        for i in range(20):
            if i >= len(lines):
                return EvaluationReason(value=0.0, reason=f"Line {i + 1} is missing")

            error = self._validate_line(lines[i].strip(), i + 1)
            if error is not None:
                return error
        return None

    async def evaluate(self, ctx: EvaluatorContext["MusicReportTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that lines 1-20 contain songs with scores in correct format."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            error = self._validate_all_lines(lines)
            if error is not None:
                return error

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking song ranking format: {e}",
            )

        return 1.0

