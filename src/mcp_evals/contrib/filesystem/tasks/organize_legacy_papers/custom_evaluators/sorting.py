"""Evaluator that checks entries are sorted correctly."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.constants import EXPECTED_YEARS

if TYPE_CHECKING:
    from pathlib import Path

    from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.task import OrganizeLegacyPapersTask


@dataclass
class Sorting(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks entries are sorted correctly."""

    def _check_summary_year_sorting(self, content: str) -> EvaluatorOutput | None:
        """Check if SUMMARY.md years are sorted. Returns None if valid, EvaluationReason if invalid."""
        years_in_summary = []
        for line in content.split("\n"):
            if "|" in line and any(year in line for year in EXPECTED_YEARS):
                for year in EXPECTED_YEARS:
                    if year in line:
                        years_in_summary.append(year)
                        break

        if years_in_summary != sorted(years_in_summary):
            return EvaluationReason(
                value=0.0,
                reason=f"SUMMARY.md years not sorted: {years_in_summary}",
            )
        return None

    def _check_index_arxiv_sorting(self, organized_dir: Path) -> EvaluatorOutput | None:
        """Check if INDEX.md arxiv IDs are sorted. Returns None if valid, EvaluationReason if invalid."""
        index_file = organized_dir / "2023" / "INDEX.md"
        if index_file.exists():
            content = index_file.read_text(encoding="utf-8")
            arxiv_ids = []
            for line in content.split("\n"):
                if "|" in line and "23" in line and "ArXiv ID" not in line and "---" not in line:
                    match = re.search(r"23\d{2}\.\d{5}", line)
                    if match:
                        arxiv_ids.append(match.group())

            if arxiv_ids != sorted(arxiv_ids):
                return EvaluationReason(
                    value=0.0,
                    reason="INDEX.md arxiv IDs not sorted in 2023/",
                )
        return None

    async def evaluate(self, ctx: EvaluatorContext[OrganizeLegacyPapersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that entries are sorted correctly."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized"

        # Check SUMMARY.md year sorting
        summary_file = organized_dir / "SUMMARY.md"
        try:
            content = summary_file.read_text(encoding="utf-8")

            error = self._check_summary_year_sorting(content)
            if error is not None:
                return error

            # Check INDEX.md arxiv ID sorting for one year
            error = self._check_index_arxiv_sorting(organized_dir)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking sorting: {e}")

        return 1.0
