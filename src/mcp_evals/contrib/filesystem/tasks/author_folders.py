"""Author Folders task for filesystem domain."""

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture


class ArxivHTMLParser(HTMLParser):
    """Parser to extract author and date information from arXiv HTML papers."""

    def __init__(self) -> None:
        """Initialize the parser with empty authors list and no publication date."""
        super().__init__()
        self.authors: list[str] = []
        self.publication_date: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle start tags to extract metadata."""
        if tag == "meta":
            attr_dict = dict(attrs)
            if attr_dict.get("name") == "citation_author":
                content = attr_dict.get("content", "")
                if content:
                    self.authors.append(content)
            elif attr_dict.get("name") in ["citation_date", "citation_online_date"]:
                content = attr_dict.get("content", "")
                if content and not self.publication_date:
                    self.publication_date = content


def extract_paper_info(html_file: Path) -> tuple[list[str], str | None]:
    """Extract authors and publication year from an HTML paper."""
    try:
        with html_file.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        parser = ArxivHTMLParser()
        parser.feed(content)

        if parser.publication_date:
            year_match = re.search(r"(\d{4})", parser.publication_date)
            year = year_match.group(1) if year_match else None
        else:
            year = None

    except (OSError, UnicodeDecodeError):
        return [], None
    else:
        return parser.authors, year


# Constants for author name normalization
SPLIT_PARTS_COUNT = 2
MIN_PAPERS_FREQUENT = 4
MIN_PAPERS_2025 = 3


def normalize_author_name(author: str) -> str:
    """Normalize author name to lowercase with underscores."""
    author = author.strip()

    parts = author.split(",", 1)
    if len(parts) == SPLIT_PARTS_COUNT:
        last_name = parts[0].strip()
        first_names = parts[1].strip()
        first_name_parts = first_names.split()
        if first_name_parts:
            first_name = first_name_parts[0]
            normalized = f"{first_name}_{last_name}"
        else:
            normalized = last_name
    else:
        normalized = author

    normalized = re.sub(r"[^\w\s-]", "", normalized)
    normalized = re.sub(r"[\s-]+", "_", normalized)
    return normalized.lower()


def analyze_papers(work_dir: Path) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    """Analyze all HTML papers and return author-paper mappings."""
    author_papers: dict[str, list[Path]] = {}
    author_2025_papers: dict[str, list[Path]] = {}

    html_files = list(work_dir.glob("*.html"))

    for html_file in html_files:
        authors, year = extract_paper_info(html_file)

        for author in authors:
            if not author:
                continue

            normalized_name = normalize_author_name(author)
            if not normalized_name:
                continue

            if normalized_name not in author_papers:
                author_papers[normalized_name] = []
            author_papers[normalized_name].append(html_file)

            if year == "2025":
                if normalized_name not in author_2025_papers:
                    author_2025_papers[normalized_name] = []
                author_2025_papers[normalized_name].append(html_file)

    return author_papers, author_2025_papers


@dataclass
class DirectoriesExist(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks required directories exist."""

    async def evaluate(self, ctx: EvaluatorContext["AuthorFoldersTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that required directories exist."""
        task = ctx.inputs
        frequent_authors_dir = task.work_dir / "frequent_authors"
        authors_2025_dir = task.work_dir / "2025_authors"

        if not frequent_authors_dir.exists():
            return EvaluationReason(value=0.0, reason="'frequent_authors' directory not found")

        if not authors_2025_dir.exists():
            return EvaluationReason(value=0.0, reason="'2025_authors' directory not found")

        if not frequent_authors_dir.is_dir():
            return EvaluationReason(value=0.0, reason="'frequent_authors' exists but is not a directory")

        if not authors_2025_dir.is_dir():
            return EvaluationReason(value=0.0, reason="'2025_authors' exists but is not a directory")

        return 1.0


@dataclass
class OriginalFilesIntact(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks original HTML files are still present (not moved)."""

    async def evaluate(self, ctx: EvaluatorContext["AuthorFoldersTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that original HTML files are still present (not moved)."""
        task = ctx.inputs
        html_files = list(task.work_dir.glob("*.html"))

        if not html_files:
            return EvaluationReason(value=0.0, reason="No original HTML files found in root directory")

        return 1.0


@dataclass
class FrequentAuthorsOrganization(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks authors with ≥4 papers have their folders and papers."""

    async def evaluate(self, ctx: EvaluatorContext["AuthorFoldersTask", AgentRunResult]) -> EvaluatorOutput:
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


@dataclass
class Authors2025Organization(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks authors with ≥3 papers in 2025 have their folders and papers."""

    async def evaluate(self, ctx: EvaluatorContext["AuthorFoldersTask", AgentRunResult]) -> EvaluatorOutput:
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


@dataclass
class NamingConvention(Evaluator["AuthorFoldersTask", AgentRunResult]):
    """Evaluator that checks author folder names follow correct naming convention."""

    async def evaluate(self, ctx: EvaluatorContext["AuthorFoldersTask", AgentRunResult]) -> EvaluatorOutput:
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


class AuthorFoldersTask(FilesystemTask):
    """Task for organizing papers by author into author-specific folders.

    The agent must:
    1. Extract author information from all HTML papers
    2. Identify authors with ≥4 papers total (frequent_authors)
    3. Identify authors with ≥3 papers in 2025 (2025_authors)
    4. Create directories and copy papers to respective folders
    """

    name = "author_folders"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You are given a directory containing multiple paper files. You have a collection of academic papers in HTML format \
from arXiv. Your task is to analyze these papers, identify authors who have published multiple papers, and organize \
them into author-specific folders based on specified criteria.

### Task Objectives

#### Part 1: Frequent Authors (≥4 papers)
1. **Extract author information** from all HTML papers in the given directory
2. **Identify authors** who appear in 4 or more papers
3. **Create a directory** `frequent_authors`
4. **Create individual folders** within this directory for each frequent author (lowercase names with underscores)
5. **Copy their papers** to their respective folders

#### Part 2: Prolific 2025 Authors (≥3 papers)
1. **Extract publication dates** along with author information
2. **Identify authors** who published 3 or more papers in 2025
3. **Create a directory** `2025_authors` for 2025 authors
4. **Create individual folders** within this directory for each prolific 2025 author (lowercase names with underscores)
5. **Copy their 2025 papers** to their respective folders

### Expected Output

#### Directory Structure:
```
[given_task_folder]/
├── [original HTML files remain untouched]
├── frequent_authors/              # Authors with ≥4 papers total
│   ├── smith_john/
│   │   └── [copied papers]
│   ├── johnson_sarah/
│   │   └── [copied papers]
│   └── ...
└── 2025_authors/                  # Authors with ≥3 papers in 2025
    ├── williams_david/
    │   └── [copied 2025 papers]
    ├── brown_emily/
    │   └── [copied 2025 papers]
    └── ...
```

#### Requirements:
- Author folder names should be **lowercase** with underscores replacing spaces/commas
  (e.g., `smith_john`, `williams_david`)
- Papers should be **copied** (not moved) to preserve originals
- Author extraction should handle various name formats correctly"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists("frequent_authors"),
            DirectoryExists("2025_authors"),
            OriginalFilesIntact(),
            FrequentAuthorsOrganization(),
            Authors2025Organization(),
            NamingConvention(),
        )
