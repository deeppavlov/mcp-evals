"""MusicMDFilesInCollections evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.project_management.constants import EXPECTED_MUSIC_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class MusicMDFilesInCollections(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks music collection markdown files are moved to personal/collections."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that music collection markdown files are moved to personal/collections."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        collections_dir = organized_dir / "personal" / "collections"

        missing_files = []
        for filename in EXPECTED_MUSIC_FILES:
            file_path = collections_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing music collection markdown files in collections: {missing_files}",
            )

        return 1.0
