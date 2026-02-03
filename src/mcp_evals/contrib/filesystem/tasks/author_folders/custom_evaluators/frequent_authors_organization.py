"""FrequentAuthorsOrganization evaluator for author_folders task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.author_folders.constants import MIN_PAPERS_FREQUENT
from mcp_evals.contrib.filesystem.tasks.author_folders.utils import analyze_papers

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.author_folders.task import AuthorFoldersTask


@dataclass
class FrequentAuthorsOrganization(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks authors with ≥4 papers have their folders and papers."""

    async def evaluate(self, ctx: EvaluatorContext[AuthorFoldersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that authors with ≥4 papers have their folders and papers."""
        task = ctx.inputs
        frequent_authors_dir = task.work_dir / "frequent_authors"

        author_papers, _ = analyze_papers(task.work_dir)

        frequent_authors = {
            author: papers for author, papers in author_papers.items() if len(papers) >= MIN_PAPERS_FREQUENT
        }

        if not frequent_authors:
            return 1.0  # No frequent authors is acceptable

        for author, expected_papers in frequent_authors.items():
            author_dir = frequent_authors_dir / author

            if not author_dir.exists():
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing directory for frequent author: {author}",
                )

            for paper in expected_papers:
                paper_copy = author_dir / paper.name
                if not paper_copy.exists():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing paper {paper.name} in {author} directory",
                    )

        # Check for unexpected directories
        try:
            for item in frequent_authors_dir.iterdir():
                if item.is_dir():
                    dir_name = item.name
                    if (
                        dir_name not in frequent_authors
                        and dir_name in author_papers
                        and len(author_papers[dir_name]) < MIN_PAPERS_FREQUENT
                    ):
                        msg = (
                            f"Author {dir_name} has only "
                            f"{len(author_papers[dir_name])} papers but has "
                            f"a folder in frequent_authors"
                        )
                        return EvaluationReason(value=0.0, reason=msg)
        except (OSError, PermissionError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking frequent_authors directory: {e}")

        return 1.0
