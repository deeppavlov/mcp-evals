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
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

Your task is to find all files that contain a substring of 30 or more characters that also appears in `large_file.txt`.\
 **You are not allowed to use python code.**

### Task Objectives

1. **Read the reference file** `large_file.txt` to understand its content
2. **Examine each file** from file_01.txt to file_20.txt
3. **Find files** that contain a substring of 30 or more characters that matches a substring in `large_file.txt`
4. **Create a file `answer.txt`** and write the results to it with the following format:
   - One line per matching file
   - Format: `filename.txt,start_position`
   - Where start_position is the character position (1-indexed) of the matching substring in `large_file.txt`
   - Do not add any things else other than `filename.txt,start_position`

### Expected Output

- File name: `answer.txt`
- Format: Each line should be `filename.txt,start_position`
- Only include files with matches of 30+ characters
- Position should be 1-indexed (first character is position 1)"""

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
