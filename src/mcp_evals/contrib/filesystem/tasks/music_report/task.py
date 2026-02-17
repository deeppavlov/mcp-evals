"""Music Report task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileContentStructure, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import (
    PopularityScoresMatchExpected,
    SongNamesMatchExpected,
    SongRankingFormat,
    SongRankingOrder,
    Top5Songs,
)


class MusicReportTask(FilesystemTask):
    """Task for analyzing music files and generating a popularity report.

    The agent must:
    1. Read song information from jay_chou/ and jj_lin/ directories
    2. Calculate popularity scores using the specified formula
    3. Generate music_analysis_report.txt with ranked songs and top 5 list
    """

    name = "music_report"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)

        self.evaluators = (
            FileExists("music/music_analysis_report.txt"),
            FileContentStructure("music/music_analysis_report.txt", expected_lines=25),
            SongRankingFormat(),
            SongRankingOrder(),
            SongNamesMatchExpected(),
            PopularityScoresMatchExpected(),
            Top5Songs(),
        )
