"""OrganizedProjectsDirectoryExists evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class OrganizedProjectsDirectoryExists(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks organized_projects directory exists."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the organized_projects directory exists."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"

        if not organized_dir.exists():
            return EvaluationReason(value=0.0, reason="'organized_projects' directory not found")

        if not organized_dir.is_dir():
            return EvaluationReason(value=0.0, reason="'organized_projects' exists but is not a directory")

        return 1.0
