"""Author Folders task for filesystem domain."""

import re
from html.parser import HTMLParser
from pathlib import Path

from .constants import SPLIT_PARTS_COUNT


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
