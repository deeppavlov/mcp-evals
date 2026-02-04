"""Authors2025Organization evaluator for author_folders task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.author_folders.constants import MIN_PAPERS_2025
from mcp_evals.contrib.filesystem.tasks.author_folders.utils import analyze_papers

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.author_folders.task import AuthorFoldersTask


@dataclass
class Authors2025Organization(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks authors with ≥3 papers in 2025 have their folders and papers."""

    async def evaluate(self, ctx: EvaluatorContext[AuthorFoldersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that authors with ≥3 papers in 2025 have their folders and papers."""
        task = ctx.inputs
        authors_2025_dir = task.work_dir / "2025_authors"

        _, author_2025_papers = analyze_papers(task.work_dir)

        prolific_2025_authors = {
            author: papers for author, papers in author_2025_papers.items() if len(papers) >= MIN_PAPERS_2025
        }

        if not prolific_2025_authors:
            return 1.0  # No prolific 2025 authors is acceptable

        for author, expected_papers in prolific_2025_authors.items():
            author_dir = authors_2025_dir / author

            if not author_dir.exists():
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing directory for 2025 author: {author}",
                )

            for paper in expected_papers:
                paper_copy = author_dir / paper.name
                if not paper_copy.exists():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing 2025 paper {paper.name} in {author} directory",
                    )

        # Check for unexpected directories
        try:
            for item in authors_2025_dir.iterdir():
                if item.is_dir():
                    dir_name = item.name
                    if (
                        dir_name not in prolific_2025_authors
                        and dir_name in author_2025_papers
                        and len(author_2025_papers[dir_name]) < MIN_PAPERS_2025
                    ):
                        msg = (
                            f"Author {dir_name} has only "
                            f"{len(author_2025_papers[dir_name])} papers in 2025 "
                            f"but has a folder in 2025_authors"
                        )
                        return EvaluationReason(value=0.0, reason=msg)
        except (OSError, PermissionError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking 2025_authors directory: {e}")

        return 1.0
