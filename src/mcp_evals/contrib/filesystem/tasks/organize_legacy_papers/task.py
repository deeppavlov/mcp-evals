"""Organize Legacy Papers task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import (
    AuthorExtraction,
    DirectoryStructure,
    IndexFiles,
    PapersMoved,
    PapersRemain,
    Sorting,
    SummaryFile,
)


class OrganizeLegacyPapersTask(FilesystemTask):
    """Task for organizing legacy papers by year with documentation.

    The agent must:
    1. Organize papers from 2023 and earlier into year-based directories
    2. Generate INDEX.md files for each year with paper metadata
    3. Create SUMMARY.md file linking to all year indexes
    4. Leave 2024+ papers in original location
    """

    name = "organize_legacy_papers"

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
