"""LearningMDFilesInResources evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.project_management.constants import EXPECTED_LEARNING_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class LearningMDFilesInResources(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks learning-related markdown files are moved to learning/resources."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that learning-related markdown files are moved to learning/resources."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        resources_dir = organized_dir / "learning" / "resources"

        missing_files = []
        for filename in EXPECTED_LEARNING_FILES:
            file_path = resources_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing learning markdown files in resources: {missing_files}",
            )

        return 1.0
