"""Timeline Extraction task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileContentStructure, FileExists, FileReadable
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.tasks.timeline_extraction.constants import (
    EXPECTED_LINE_COUNT,
)
from mcp_evals.contrib.filesystem.tasks.timeline_extraction.custom_evaluators import (
    ChronologicalOrder,
    DateFormat,
    ExpectedEntries,
    FilePathsExist,
    LineFormat,
    NoDuplicates,
)
from mcp_evals.contrib.filesystem.utils import Fixture


class TimelineExtractionTask(FilesystemTask):
    """Task for extracting timeline information from files.

    The agent must:
    1. Read all files under current path
    2. Extract time/plan information indicating 2024
    3. Create timeline.txt with file_path:time format
    4. Sort by chronological order
    """

    name = "timeline_extraction"
    goal = """Please use FileSystem tools to finish the following task:

Read all the files under current path, extract every time/plan information that clearly indicates 2024, and \
integrate them into a list and create a file in main directory called `timeline.txt`. Write the timeline in \
the file in the following format.

### Rules
- If a task only shows month without day, use the 1st day of that month
- If a task only shows year without month and day, skip it.
- If a file shows multiple tasks on the same date, count only once per date

### Output Format
- Each line format: `file_path:time`
    - `file_path`: The file path where this time information appears (**relative to the current path**)
    - `time`: Specific time, if it's a time period, write the start time (YYYY-MM-DD)

### Sorting Requirements
- Sort by chronological order"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("timeline.txt"),
            FileReadable("timeline.txt"),
            FileContentStructure("timeline.txt", expected_lines=EXPECTED_LINE_COUNT),
            LineFormat(),
            DateFormat(),
            ChronologicalOrder(),
            ExpectedEntries(),
            NoDuplicates(),
            FilePathsExist(),
        )
