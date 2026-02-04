"""Evaluator that checks SUMMARY.md exists and has correct content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.constants import EXPECTED_COUNTS, EXPECTED_YEARS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.task import OrganizeLegacyPapersTask


@dataclass
class SummaryFile(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks SUMMARY.md exists and has correct content."""

    def _check_required_columns(self, content: str) -> EvaluatorOutput | None:
        """Check if SUMMARY.md has required columns. Returns None if valid, EvaluationReason if invalid."""
        if "Year" not in content or "Paper Count" not in content or "Index Link" not in content:
            return EvaluationReason(value=0.0, reason="SUMMARY.md missing required columns")
        return None

    def _check_years_and_links(self, content: str) -> EvaluatorOutput | None:
        """Check if all years and links are present. Returns None if valid, EvaluationReason if invalid."""
        for year in EXPECTED_YEARS:
            if year not in content:
                return EvaluationReason(value=0.0, reason=f"SUMMARY.md missing year {year}")

            link = f"{year}/INDEX.md"
            if link not in content:
                return EvaluationReason(value=0.0, reason=f"SUMMARY.md missing link to {link}")
        return None

    def _check_paper_counts(self, content: str) -> EvaluatorOutput | None:
        """Check if paper counts are correct. Returns None if valid, EvaluationReason if invalid."""
        for year, count in EXPECTED_COUNTS.items():
            for line in content.split("\n"):
                if f"| {year}" in line or f"|{year}" in line:
                    if str(count) not in line:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"SUMMARY.md has incorrect paper count for {year}",
                        )
                    break
        return None

    async def evaluate(self, ctx: EvaluatorContext[OrganizeLegacyPapersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify SUMMARY.md exists and has correct content."""
        task = ctx.inputs
        summary_file = task.work_dir / "organized" / "SUMMARY.md"

        if not summary_file.exists():
            return EvaluationReason(value=0.0, reason="SUMMARY.md not found")

        try:
            content = summary_file.read_text(encoding="utf-8")

            error = self._check_required_columns(content)
            if error is not None:
                return error

            error = self._check_years_and_links(content)
            if error is not None:
                return error

            error = self._check_paper_counts(content)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading SUMMARY.md: {e}")

        return 1.0
