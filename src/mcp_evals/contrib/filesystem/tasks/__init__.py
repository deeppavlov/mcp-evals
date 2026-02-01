"""Filesystem tasks for MCP Universe evaluations."""

from mcp_evals.contrib.filesystem.tasks.duplicates_searching import DuplicatesSearchingTask
from mcp_evals.contrib.filesystem.tasks.music_report import MusicReportTask

__all__ = [
    "DuplicatesSearchingTask",
    "MusicReportTask",
]
