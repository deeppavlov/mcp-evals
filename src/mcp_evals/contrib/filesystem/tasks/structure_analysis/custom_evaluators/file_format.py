"""FileFormat evaluator for structure_analysis task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.structure_analysis.task import StructureAnalysisTask


@dataclass
class FileFormat(Evaluator["StructureAnalysisTask", AgentRunResult]):
    """Evaluator that checks structure_analysis.txt file has proper format."""

    async def evaluate(self, ctx: EvaluatorContext[StructureAnalysisTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the structure_analysis.txt file has proper format."""
        task = ctx.inputs
        analysis_file = task.work_dir / "structure_analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            if len(lines) < 5:  # noqa: PLR2004
                return EvaluationReason(
                    value=0.0,
                    reason="File seems too short to contain all required information",
                )

            if not content.strip():
                return EvaluationReason(value=0.0, reason="File is completely empty")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file format: {e}")

        return 1.0
