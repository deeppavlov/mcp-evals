"""EntertainmentMDFilesInEntertainment evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.project_management.constants import EXPECTED_ENTERTAINMENT_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class EntertainmentMDFilesInEntertainment(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks entertainment planning markdown files are moved to personal/entertainment."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that entertainment planning markdown files are moved to personal/entertainment."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        entertainment_dir = organized_dir / "personal" / "entertainment"

        missing_files = []
        for filename in EXPECTED_ENTERTAINMENT_FILES:
            file_path = entertainment_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing entertainment markdown files in entertainment: {missing_files}",
            )

        return 1.0
