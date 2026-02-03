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
    goal = """Please use FileSystem tools to finish the following task:

Please help me identify duplicate names from the list of all the 150 students. Do not use python code.
Then generate a `namesake.txt` file to record the results in the following format,
with each group written in three lines:

name: xxx
count: xxx
ids: xxx, xxx, ...

Leave one blank line between every two groups.
If there are multiple duplicates, just list all corresponding IDs in the third line.

### Expected Output

- File name: `namesake.txt`
- Format: Three lines per duplicate name group (name, count, ids)
- Blank line separator between groups
- Exactly 16 duplicate names should be identified
- Each duplicate name should have exactly 2 student IDs"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("namesake.txt"),
            ExpectedResults(),
        )

