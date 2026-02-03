"""ProgressTrackingEmpty evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class ProgressTrackingEmpty(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks progress_tracking directory is empty."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that progress_tracking directory is empty."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        progress_dir = organized_dir / "learning" / "progress_tracking"

        try:
            files_in_progress = list(progress_dir.iterdir())
            if files_in_progress:
                file_names = [f.name for f in files_in_progress]
                msg = f"progress_tracking directory should be empty, but contains: {file_names}"
                return EvaluationReason(value=0.0, reason=msg)
        except (OSError, PermissionError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking progress_tracking directory: {e}",
            )

        return 1.0
