"""Uppercase task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists, FileExists, FilesExistInDirectory
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.tasks.uppercase.constants import EXPECTED_FILES
from mcp_evals.contrib.filesystem.tasks.uppercase.custom_evaluators import (
    AllFilesAreIncluded,
    AnswerFormat,
    UppercaseContent,
    WordCountsAreCorrect,
)
from mcp_evals.contrib.filesystem.utils import Fixture


class UppercaseTask(FilesystemTask):
    """Task for converting files to uppercase and counting words.

    The agent must:
    1. Create an uppercase directory
    2. Convert each file from file_01.txt to file_10.txt to uppercase
    3. Save converted files in uppercase/ directory
    4. Count words in each original file
    5. Create answer.txt with word counts in specified format
    """

    name = "uppercase"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            DirectoryExists("uppercase"),
            FilesExistInDirectory("uppercase", EXPECTED_FILES),
            UppercaseContent(),
            FileExists("uppercase/answer.txt"),
            AnswerFormat(),
            AllFilesAreIncluded(),
            WordCountsAreCorrect(),
        )
