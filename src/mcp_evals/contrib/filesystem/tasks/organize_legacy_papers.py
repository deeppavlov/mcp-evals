"""Organize Legacy Papers task for filesystem domain."""

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected paper distribution
EXPECTED_PAPERS = {
    "2017": ["1707.06347.html"],
    "2021": ["2105.04165.html"],
    "2022": ["2201.11903.html"],
    "2023": [
        "2303.08774.html",
        "2306.08640.html",
        "2310.02255.html",
        "2310.08446.html",
        "2312.00849.html",
        "2312.07533.html",
        "2312.11805.html",
    ],
}

EXPECTED_YEARS = ["2017", "2021", "2022", "2023"]

EXPECTED_COUNTS = {
    "2017": 1,
    "2021": 1,
    "2022": 1,
    "2023": 7,
}

# Constants for year parsing
MIN_ARXIV_ID_LENGTH = 2
YEAR_THRESHOLD_2024 = 24
MAX_AUTHORS_FOR_DISPLAY = 3


@dataclass
class PapersRemain(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks BibTeX and 2024+ papers remain in original directory."""

    async def evaluate(self, ctx: EvaluatorContext["OrganizeLegacyPapersTask", AgentRunResult]) -> EvaluatorOutput:
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


@dataclass
class DirectoryStructure(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks organized directory structure exists."""

    async def evaluate(self, ctx: EvaluatorContext["OrganizeLegacyPapersTask", AgentRunResult]) -> EvaluatorOutput:
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


@dataclass
class PapersMoved(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks papers are correctly moved to year folders."""

    async def evaluate(self, ctx: EvaluatorContext["OrganizeLegacyPapersTask", AgentRunResult]) -> EvaluatorOutput:
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


@dataclass
class IndexFiles(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks INDEX.md files exist and have correct format."""

    async def evaluate(self, ctx: EvaluatorContext["OrganizeLegacyPapersTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify INDEX.md files exist and have correct format."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized"

        for year in EXPECTED_YEARS:
            index_file = organized_dir / year / "INDEX.md"

            if not index_file.exists():
                return EvaluationReason(value=0.0, reason=f"INDEX.md missing in {year}/")

            try:
                content = index_file.read_text(encoding="utf-8")

                if "ArXiv ID" not in content or "Authors" not in content or "Local Path" not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"INDEX.md in {year}/ missing required columns",
                    )

                year_dir = organized_dir / year
                html_files = list(year_dir.glob("*.html"))
                for html_file in html_files:
                    arxiv_id = html_file.stem
                    if arxiv_id not in content:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"INDEX.md in {year}/ missing paper {arxiv_id}",
                        )
            except (OSError, UnicodeDecodeError) as e:
                return EvaluationReason(value=0.0, reason=f"Error reading INDEX.md in {year}/: {e}")

        return 1.0


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

    async def evaluate(self, ctx: EvaluatorContext["OrganizeLegacyPapersTask", AgentRunResult]) -> EvaluatorOutput:
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

    async def evaluate(self, ctx: EvaluatorContext["OrganizeLegacyPapersTask", AgentRunResult]) -> EvaluatorOutput:
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

    async def evaluate(self, ctx: EvaluatorContext["OrganizeLegacyPapersTask", AgentRunResult]) -> EvaluatorOutput:
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


class OrganizeLegacyPapersTask(FilesystemTask):
    """Task for organizing legacy papers by year with documentation.

    The agent must:
    1. Organize papers from 2023 and earlier into year-based directories
    2. Generate INDEX.md files for each year with paper metadata
    3. Create SUMMARY.md file linking to all year indexes
    4. Leave 2024+ papers in original location
    """

    name = "organize_legacy_papers"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You are given a directory containing multiple paper files. You have a collection of arXiv papers saved as HTML files
in the papers directory, along with a BibTeX file. Your task is to organize the older papers (2023 and earlier) into
a structured year-based hierarchy with proper documentation, while leaving newer papers in the original location.

### Task Objectives

1. **Organize by year**: Create a year-based directory structure for papers from 2023 and earlier
2. **Generate documentation**: Create INDEX.md files for each year with paper metadata
3. **Create summary**: Build a master SUMMARY.md file linking to all year indexes

### Detailed Requirements

#### Step 1: Organization
- Create directory structure: `organized/{year}/` where year is extracted from the arXiv ID
  - Example: `1707.06347.html` → `organized/2017/1707.06347.html`
- Move each HTML file from 2023 and earlier to its corresponding year folder, keeping original filenames
- Papers from 2024 onwards (arXiv IDs starting with `24` or `25`) should remain in the original papers directory

#### Step 2: Year Index Files
For each year folder, create an `INDEX.md` file containing:
- A markdown table with three columns: `ArXiv ID | Authors | Local Path`
- Extract authors from `<meta name="citation_author" content="..."/>` tags, keeping only the first 3 authors
- If there are more than 3 authors, list the first 3 followed by "et al."
- Format authors as: "Author1, Author2, Author3" or "Author1, Author2, Author3, et al."
- Local Path should be just the filename (e.g., `1707.06347.html`)
- Sort entries by arXiv ID in ascending order

#### Step 3: Master Summary
Create `organized/SUMMARY.md` with:
- A markdown table with columns: `Year | Paper Count | Index Link`
- Index Link should be a relative markdown link (e.g., `[View Index](2017/INDEX.md)`)
- Sort by year in ascending order

### Expected Output Structure

```
papers/
├── arxiv_2025.bib (remains here)
├── (2024+ HTML files remain here)
└── organized/
    ├── SUMMARY.md
    ├── 2017/
    │   ├── INDEX.md
    │   └── 1707.06347.html
    ├── 2021/
    │   ├── INDEX.md
    │   └── 2105.04165.html
    ├── 2022/
    │   ├── INDEX.md
    │   └── 2201.11903.html
    └── 2023/
        ├── INDEX.md
        ├── 2303.08774.html
        ├── 2306.08640.html
        ├── 2310.02255.html
        ├── 2310.08446.html
        ├── 2312.00849.html
        ├── 2312.07533.html
        └── 2312.11805.html
```"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            PapersRemain(),
            DirectoryStructure(),
            PapersMoved(),
            IndexFiles(),
            AuthorExtraction(),
            SummaryFile(),
            Sorting(),
        )
