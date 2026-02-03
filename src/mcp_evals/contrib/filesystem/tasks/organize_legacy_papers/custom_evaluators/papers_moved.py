"""Evaluator that checks papers are correctly moved to year folders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.constants import EXPECTED_PAPERS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.task import OrganizeLegacyPapersTask


@dataclass
class PapersMoved(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks papers are correctly moved to year folders."""

    async def evaluate(self, ctx: EvaluatorContext[OrganizeLegacyPapersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify papers are correctly moved to year folders."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized"

        for year, papers in EXPECTED_PAPERS.items():
            year_dir = organized_dir / year
            if not year_dir.exists():
                return EvaluationReason(value=0.0, reason=f"Year directory {year} doesn't exist")

            try:
                actual_papers = sorted([f.name for f in year_dir.glob("*.html")])
                expected_sorted = sorted(papers)

                if actual_papers != expected_sorted:
                    return EvaluationReason(
                        value=0.0,
                        reason=(
                            f"Papers in {year}/ don't match expected. "
                            f"Expected: {expected_sorted}, Found: {actual_papers}"
                        ),
                    )
            except (OSError, PermissionError) as e:
                return EvaluationReason(value=0.0, reason=f"Error checking papers in {year}/: {e}")

        return 1.0
