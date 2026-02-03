"""DirectoryStructure evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.project_management.constants import REQUIRED_DIRS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class DirectoryStructure(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks all required subdirectories exist."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required subdirectories exist."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"

        missing_dirs = []
        for dir_path in REQUIRED_DIRS:
            full_path = organized_dir / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
            elif not full_path.is_dir():
                missing_dirs.append(f"{dir_path} (not a directory)")

        if missing_dirs:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing or invalid directories: {missing_dirs}",
            )

        return 1.0
