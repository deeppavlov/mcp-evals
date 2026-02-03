"""FilePathsExist evaluator for timeline_extraction task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.timeline_extraction.utils import _extract_file_path_from_line

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.timeline_extraction.task import TimelineExtractionTask


@dataclass
class FilePathsExist(Evaluator["TimelineExtractionTask", AgentRunResult]):
    """Evaluator that checks all file paths mentioned in timeline.txt actually exist."""

    async def evaluate(self, ctx: EvaluatorContext[TimelineExtractionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all file paths mentioned in timeline.txt actually exist."""
        task = ctx.inputs
        timeline_file = task.work_dir / "timeline.txt"

        try:
            content = timeline_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            missing_files = []
            for line in lines:
                file_path = _extract_file_path_from_line(line)
                if file_path:
                    full_path = task.work_dir / file_path
                    if not full_path.exists():
                        missing_files.append(file_path)

            if missing_files:
                msg = f"{len(missing_files)} referenced files do not exist. Examples: {missing_files[:3]}"
                return EvaluationReason(value=0.0, reason=msg)
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file paths: {e}")

        return 1.0
