"""Evaluator that checks organized directory structure exists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.constants import EXPECTED_YEARS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.task import OrganizeLegacyPapersTask


@dataclass
class DirectoryStructure(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks organized directory structure exists."""

    async def evaluate(self, ctx: EvaluatorContext[OrganizeLegacyPapersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify the organized directory structure exists."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized"

        if not organized_dir.exists():
            return EvaluationReason(value=0.0, reason="organized/ directory not found")

        found_years = []
        for year in EXPECTED_YEARS:
            year_dir = organized_dir / year
            if year_dir.exists() and year_dir.is_dir():
                found_years.append(year)

        if len(found_years) != len(EXPECTED_YEARS):
            return EvaluationReason(
                value=0.0,
                reason=f"Expected year directories {EXPECTED_YEARS}, found {found_years}",
            )

        return 1.0
