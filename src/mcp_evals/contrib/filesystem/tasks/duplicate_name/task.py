"""Duplicate Name task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import ExpectedResults


class DuplicateNameTask(FilesystemTask):
    """Task for identifying duplicate names from student database.

    The agent must:
    1. Identify duplicate names from 150 students
    2. Generate namesake.txt with format: name, count, ids
    3. Find exactly 16 duplicate names
    4. Each duplicate name should have exactly 2 student IDs
    """

    name = "duplicate_name"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("namesake.txt"),
            ExpectedResults(),
        )
