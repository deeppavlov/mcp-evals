"""SongRankingOrder evaluator for music_report task."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.music_report.task import MusicReportTask


class SongRankingOrder(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks songs are ranked by popularity score in descending order."""

    async def evaluate(self, ctx: EvaluatorContext[MusicReportTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that songs are ranked by popularity score in descending order."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            scores = []
            for i in range(20):
                if i >= len(lines):
                    return EvaluationReason(value=0.0, reason=f"Line {i + 1} is missing")

                line = lines[i].strip()
                parts = line.split(":", 1)
                score = float(parts[1].strip())
                scores.append(score)

            # Check if scores are in descending order, allowing equal scores to be adjacent
            for i in range(1, len(scores)):
                if scores[i] > scores[i - 1]:
                    msg = f"Scores not in descending order: {scores[i - 1]} < {scores[i]} at line {i + 1}"
                    return EvaluationReason(value=0.0, reason=msg)

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking song ranking order: {e}",
            )
        else:
            return 1.0

