"""DirectoriesExist evaluator for author_folders task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.author_folders.task import AuthorFoldersTask


@dataclass
class DirectoriesExist(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks required directories exist."""

    async def evaluate(self, ctx: EvaluatorContext[AuthorFoldersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that required directories exist."""
        task = ctx.inputs
        frequent_authors_dir = task.work_dir / "frequent_authors"
        authors_2025_dir = task.work_dir / "2025_authors"

        if not frequent_authors_dir.exists():
            return EvaluationReason(value=0.0, reason="'frequent_authors' directory not found")

        if not authors_2025_dir.exists():
            return EvaluationReason(value=0.0, reason="'2025_authors' directory not found")

        if not frequent_authors_dir.is_dir():
            return EvaluationReason(value=0.0, reason="'frequent_authors' exists but is not a directory")

        if not authors_2025_dir.is_dir():
            return EvaluationReason(value=0.0, reason="'2025_authors' exists but is not a directory")

        return 1.0
