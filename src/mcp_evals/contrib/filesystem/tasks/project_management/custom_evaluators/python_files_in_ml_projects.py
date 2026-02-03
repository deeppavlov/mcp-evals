"""PythonFilesInMLProjects evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.project_management.constants import EXPECTED_PYTHON_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class PythonFilesInMLProjects(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks all Python files are moved to experiments/ml_projects."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all Python files are moved to experiments/ml_projects."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        ml_projects_dir = organized_dir / "experiments" / "ml_projects"

        missing_files = []
        for filename in EXPECTED_PYTHON_FILES:
            file_path = ml_projects_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing Python files in ml_projects: {missing_files}",
            )

        return 1.0
