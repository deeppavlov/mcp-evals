"""Filesystem domain for MCP Universe filesystem evaluations."""

from collections.abc import Sequence

from pydantic_ai.mcp import MCPServerStdio

from mcp_evals import Domain
from mcp_evals.contrib.filesystem.tasks.duplicates_searching import DuplicatesSearchingTask
from mcp_evals.contrib.filesystem.tasks.music_report import MusicReportTask


class FilesystemDomain(Domain):
    """Domain for filesystem tasks from MCP Universe.

    Provides MCP filesystem server and groups related filesystem tasks.
    The FILESYSTEM_ROOT environment variable is set by individual tasks
    during their setup() phase.
    """

    name = "filesystem"

    def mcp_servers(self) -> Sequence[MCPServerStdio]:
        """Return MCP filesystem server configuration.

        The server uses FILESYSTEM_ROOT environment variable which is set
        by tasks during setup(). Each task sets it to its isolated workspace.
        """
        return [MCPServerStdio("uvx", "mcp-server-filesystem")]

    def tasks(self) -> Sequence[MusicReportTask | DuplicatesSearchingTask]:
        """Return all filesystem tasks."""
        return [MusicReportTask(), DuplicatesSearchingTask()]
