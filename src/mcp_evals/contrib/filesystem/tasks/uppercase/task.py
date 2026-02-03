"""Uppercase task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.tasks.uppercase.custom_evaluators import (
    AllFilesAreIncluded,
    AnswerFormat,
    UppercaseContent,
    UppercaseFilesExist,
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
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You need to process 10 text files (file_01.txt to file_10.txt) and convert their content to uppercase format.

### Task Objectives

1. **Create an uppercase directory** in the test environment root
2. **Convert each file** from file_01.txt to file_10.txt to uppercase
3. **Save converted files** in the uppercase/ directory with the same names
4. **Count words** in each original file (file_01.txt to file_10.txt)
5. **Create answer.txt** with word counts in the specified format

### Specified Format of answer.txt

Create a file named `answer.txt` in the `uppercase/` directory

**Requirements:**

- Each line should follow the format: `<filename>:<word_count>`
- Include all 10 files: file_01.txt, file_02.txt, ..., file_10.txt
- Use the exact filename format (file_01.txt, file_02.txt, etc.)
- One entry per line
- Total of 10 lines

### Expected Output

- Directory: `uppercase/`
- Files: `file_01.txt` to `file_10.txt` (all in uppercase)
- File: `uppercase/answer.txt` with word counts"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists("uppercase"),
            UppercaseFilesExist(),
            UppercaseContent(),
            FileExists("uppercase/answer.txt"),
            AnswerFormat(),
            AllFilesAreIncluded(),
            WordCountsAreCorrect(),
        )
