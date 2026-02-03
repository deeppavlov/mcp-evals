"""Evaluator that checks authors are correctly extracted from HTML metadata (max 3 authors)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.constants import EXPECTED_YEARS, MAX_AUTHORS_FOR_DISPLAY

if TYPE_CHECKING:
    from pathlib import Path

    from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.task import OrganizeLegacyPapersTask


@dataclass
class AuthorExtraction(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks authors are correctly extracted from HTML metadata (max 3 authors)."""

    def _check_many_authors_line(self, line: str, all_authors: list[str]) -> EvaluatorOutput | None:
        """Check line for papers with >3 authors. Returns None if valid, EvaluationReason if invalid."""
        if "et al." not in line:
            return EvaluationReason(
                value=0.0,
                reason="Missing 'et al.' for paper with >3 authors",
            )
        for author in all_authors[:MAX_AUTHORS_FOR_DISPLAY]:
            if author not in line:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Author '{author}' not found in INDEX.md",
                )
        if all_authors[MAX_AUTHORS_FOR_DISPLAY] in line:
            return EvaluationReason(
                value=0.0,
                reason=(f"Fourth author '{all_authors[MAX_AUTHORS_FOR_DISPLAY]}' should not be in INDEX.md"),
            )
        return None

    def _check_few_authors_line(self, line: str, all_authors: list[str]) -> EvaluatorOutput | None:
        """Check line for papers with ≤3 authors. Returns None if valid, EvaluationReason if invalid."""
        if "et al." in line:
            return EvaluationReason(
                value=0.0,
                reason="Should not have 'et al.' for paper with ≤3 authors",
            )
        for author in all_authors:
            if author not in line:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Author '{author}' not found in INDEX.md",
                )
        return None

    def _check_sample_paper_authors(self, all_authors: list[str], index_content: str) -> EvaluatorOutput | None:
        """Check sample paper's authors in INDEX.md. Returns None if valid, EvaluationReason if invalid."""
        for line in index_content.split("\n"):
            if "1707.06347" in line:
                if len(all_authors) > MAX_AUTHORS_FOR_DISPLAY:
                    error = self._check_many_authors_line(line, all_authors)
                    if error is not None:
                        return error
                else:
                    error = self._check_few_authors_line(line, all_authors)
                    if error is not None:
                        return error
                return None

        return EvaluationReason(value=0.0, reason="Paper 1707.06347 not found in INDEX.md")

    def _check_paper_author_line(
        self, line: str, authors: list[str], year: str, arxiv_id: str
    ) -> EvaluatorOutput | None:
        """Check a single paper's author line. Returns None if valid, EvaluationReason if invalid."""
        if len(authors) > MAX_AUTHORS_FOR_DISPLAY and "et al." not in line:
            msg = f"{year}/{arxiv_id}: Missing 'et al.' for {len(authors)} authors"
            return EvaluationReason(value=0.0, reason=msg)
        if len(authors) <= MAX_AUTHORS_FOR_DISPLAY and "et al." in line:
            msg = f"{year}/{arxiv_id}: Unexpected 'et al.' for {len(authors)} authors"
            return EvaluationReason(value=0.0, reason=msg)

        author_parts = line.split("|")[1] if "|" in line else ""
        author_count = author_parts.count(",") + 1 if author_parts.strip() else 0
        if "et al." in author_parts:
            author_count -= 1

        if author_count > MAX_AUTHORS_FOR_DISPLAY:
            return EvaluationReason(
                value=0.0,
                reason=f"{year}/{arxiv_id}: More than 3 authors listed",
            )
        return None

    def _check_year_papers(self, organized_dir: Path, year: str) -> EvaluatorOutput | None:
        """Check all papers in a year directory. Returns None if valid, EvaluationReason if invalid."""
        year_dir = organized_dir / year
        if not year_dir.exists():
            return None

        index_file = year_dir / "INDEX.md"
        if not index_file.exists():
            return None

        index_content = index_file.read_text(encoding="utf-8")

        for html_file in year_dir.glob("*.html"):
            arxiv_id = html_file.stem

            html_content = html_file.read_text(encoding="utf-8")
            authors = re.findall(r'<meta name="citation_author" content="([^"]+)"', html_content)

            for line in index_content.split("\n"):
                if arxiv_id in line and "|" in line and "ArXiv ID" not in line:
                    error = self._check_paper_author_line(line, authors, year, arxiv_id)
                    if error is not None:
                        return error
                    break
        return None

    def _check_all_papers_author_limits(self, organized_dir: Path) -> EvaluatorOutput | None:
        """Check 3-author limit across all papers. Returns None if valid, EvaluationReason if invalid."""
        for year in EXPECTED_YEARS:
            error = self._check_year_papers(organized_dir, year)
            if error is not None:
                return error
        return None

    async def evaluate(self, ctx: EvaluatorContext[OrganizeLegacyPapersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that authors are correctly extracted from HTML metadata (max 3 authors)."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized"

        # Check a sample paper's authors
        sample_file = organized_dir / "2017" / "1707.06347.html"
        if not sample_file.exists():
            return EvaluationReason(
                value=0.0,
                reason="Cannot verify author extraction - sample file missing",
            )

        try:
            html_content = sample_file.read_text(encoding="utf-8")
            author_pattern = r'<meta name="citation_author" content="([^"]+)"'
            all_authors = re.findall(author_pattern, html_content)

            if not all_authors:
                return EvaluationReason(value=0.0, reason="No authors found in sample HTML file")

            index_file = organized_dir / "2017" / "INDEX.md"
            index_content = index_file.read_text(encoding="utf-8")

            error = self._check_sample_paper_authors(all_authors, index_content)
            if error is not None:
                return error

            # Additional check: verify 3-author limit across all papers
            error = self._check_all_papers_author_limits(organized_dir)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying author extraction: {e}")

        return 1.0
