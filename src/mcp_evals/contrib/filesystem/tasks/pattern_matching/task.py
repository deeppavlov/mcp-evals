"""Pattern Matching task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import AnswerFormat, FilesExist, MatchesAreCorrect, MatchLengthIs30Plus


class PatternMatchingTask(FilesystemTask):
    """Task for finding files with common substrings of 30+ characters.

    The agent must:
    1. Read the reference file large_file.txt
    2. Examine each file from file_01.txt to file_20.txt
    3. Find files with substrings of 30+ characters matching large_file.txt
    4. Create answer.txt with results in format: filename.txt,start_position
    """

    name = "pattern_matching"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("answer.txt"),
            AnswerFormat(),
            FilesExist(),
            MatchLengthIs30Plus(),
            MatchesAreCorrect(),
        )
