"""Dispute Review task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import ExpectedEntries, OutputFormat


class DisputeReviewTask(FilesystemTask):
    """Task for reviewing legal document disputes and counting comments.

    The agent must:
    1. Review versions v5, v6, v7 in legal_files/
    2. Identify all clauses that have been commented
    3. Generate dispute_review.txt with format: Clause number:number of comments
    """

    name = "dispute_review"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("dispute_review.txt"),
            OutputFormat(),
            ExpectedEntries(),
        )
