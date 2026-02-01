"""Filesystem domain and tasks for MCP Universe filesystem evaluations."""

from mcp_evals.contrib.filesystem.domain import FilesystemDomain
from mcp_evals.contrib.filesystem.tasks.duplicates_searching import DuplicatesSearchingTask
from mcp_evals.contrib.filesystem.tasks.music_report import MusicReportTask

__all__ = [
    "DuplicatesSearchingTask",
    "FilesystemDomain",
    "MusicReportTask",
]
