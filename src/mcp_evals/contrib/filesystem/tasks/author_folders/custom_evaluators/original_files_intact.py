"""OriginalFilesIntact evaluator for author_folders task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.author_folders.task import AuthorFoldersTask


@dataclass
class OriginalFilesIntact(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks original HTML files are still present (not moved)."""

    async def evaluate(self, ctx: EvaluatorContext[AuthorFoldersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that original HTML files are still present (not moved)."""
        task = ctx.inputs
        html_files = list(task.work_dir.glob("*.html"))

        if not html_files:
            return EvaluationReason(value=0.0, reason="No original HTML files found in root directory")

        return 1.0
