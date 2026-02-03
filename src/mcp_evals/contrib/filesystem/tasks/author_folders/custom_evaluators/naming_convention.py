"""NamingConvention evaluator for author_folders task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.author_folders.task import AuthorFoldersTask


@dataclass
class NamingConvention(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks author folder names follow correct naming convention."""

    async def evaluate(self, ctx: EvaluatorContext[AuthorFoldersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that author folder names follow the correct naming convention."""
        task = ctx.inputs
        frequent_authors_dir = task.work_dir / "frequent_authors"
        authors_2025_dir = task.work_dir / "2025_authors"

        try:
            for author_dir in frequent_authors_dir.iterdir():
                if author_dir.is_dir():
                    name = author_dir.name
                    if not re.match(r"^[a-z0-9_]+$", name):
                        msg = f"Invalid folder name in frequent_authors: {name} (should be lowercase with underscores)"
                        return EvaluationReason(value=0.0, reason=msg)

            for author_dir in authors_2025_dir.iterdir():
                if author_dir.is_dir():
                    name = author_dir.name
                    if not re.match(r"^[a-z0-9_]+$", name):
                        msg = f"Invalid folder name in 2025_authors: {name} (should be lowercase with underscores)"
                        return EvaluationReason(value=0.0, reason=msg)
        except (OSError, PermissionError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking naming convention: {e}")

        return 1.0
