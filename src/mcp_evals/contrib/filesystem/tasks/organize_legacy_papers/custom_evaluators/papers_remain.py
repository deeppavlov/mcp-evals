"""Evaluator that checks BibTeX and 2024+ papers remain in original directory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.constants import (
    MIN_ARXIV_ID_LENGTH,
    YEAR_THRESHOLD_2024,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.task import OrganizeLegacyPapersTask


@dataclass
class PapersRemain(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks BibTeX and 2024+ papers remain in original directory."""

    async def evaluate(self, ctx: EvaluatorContext[OrganizeLegacyPapersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that BibTeX and 2024+ papers remain in original directory."""
        task = ctx.inputs

        # Check BibTeX file still exists
        bib_file = task.work_dir / "arxiv_2025.bib"
        if not bib_file.exists():
            return EvaluationReason(value=0.0, reason="BibTeX file arxiv_2025.bib not found")

        # Check that pre-2024 papers are NOT in original directory
        pre_2024_found = []
        try:
            for html_file in task.work_dir.glob("*.html"):
                arxiv_id = html_file.stem
                year_part = arxiv_id[:MIN_ARXIV_ID_LENGTH] if len(arxiv_id) >= MIN_ARXIV_ID_LENGTH else ""
                if year_part.isdigit():
                    year = int(year_part)
                    if year < YEAR_THRESHOLD_2024:
                        pre_2024_found.append(html_file.name)
        except (OSError, PermissionError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking papers: {e}")

        if pre_2024_found:
            return EvaluationReason(
                value=0.0,
                reason=f"Pre-2024 papers still in original directory: {pre_2024_found[:3]}",
            )

        return 1.0
