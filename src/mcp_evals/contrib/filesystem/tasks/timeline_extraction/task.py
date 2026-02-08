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
