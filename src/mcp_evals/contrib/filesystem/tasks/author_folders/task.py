"""Author Folders task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import DirectoriesExist
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import (
    Authors2025Organization,
    FrequentAuthorsOrganization,
    NamingConvention,
    OriginalFilesIntact,
)


class AuthorFoldersTask(FilesystemTask):
    """Task for organizing papers by author into author-specific folders.

    The agent must:
    1. Extract author information from all HTML papers
    2. Identify authors with ≥4 papers total (frequent_authors)
    3. Identify authors with ≥3 papers in 2025 (2025_authors)
    4. Create directories and copy papers to respective folders
    """

    name = "author_folders"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            DirectoriesExist(["frequent_authors", "2025_authors"]),
            OriginalFilesIntact(),
            FrequentAuthorsOrganization(),
            Authors2025Organization(),
            NamingConvention(),
        )
