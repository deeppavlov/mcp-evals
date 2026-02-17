"""Contact Information task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FileInDirectory
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import AnswerContent, CSVContentAccuracy, CSVDataCompleteness, CSVStructure


class ContactInformationTask(FilesystemTask):
    """Task for compiling contact information from all files into a CSV table.

    The agent must:
    1. Scan all files in the directory
    2. Extract contact information for all individuals and organizations
    3. Create contact_info.csv with Name, Email, Phone columns
    4. Answer what is Charlie Davis's job/profession in answer.txt
    """

    name = "contact_information"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("contact_info.csv"),
            FileExists("answer.txt"),
            FileInDirectory("contact_info.csv", expected_directory=None),
            FileInDirectory("answer.txt", expected_directory=None),
            CSVStructure(),
            CSVContentAccuracy(),
            CSVDataCompleteness(),
            AnswerContent(),
        )
