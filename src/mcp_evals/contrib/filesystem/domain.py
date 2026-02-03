"""Filesystem domain for MCP Universe filesystem evaluations."""

from collections.abc import Sequence
from contextlib import AsyncExitStack
from pathlib import Path

import aiofiles
from loguru import logger
from pydantic_ai.mcp import MCPServerStdio

from mcp_evals import Domain
from mcp_evals.contrib.filesystem.tasks.duplicates_searching import DuplicatesSearchingTask
from mcp_evals.contrib.filesystem.tasks.music_report import MusicReportTask


class FilesystemDomain(Domain):
    """Domain for filesystem tasks from MCP Universe.

    Provides MCP filesystem server and groups related filesystem tasks.
    """

    name = "filesystem"
    _stack: AsyncExitStack | None = None

    async def setup(self) -> None:
        """Creeate tmp dir for filesystem operations."""
        if self._stack is not None:
            msg = "Attempted to create FilesystemDomain again"
            raise RuntimeError(msg)

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        logger.debug(f"[{self.name}] Creating workspace directory...")
        tmpdir_ctx = aiofiles.tempfile.TemporaryDirectory(prefix="mcp-filesystem-")
        self._tmp_dir = Path(await self._stack.enter_async_context(tmpdir_ctx))

    async def teardown(self) -> None:  # noqa: D102
        if self._stack is None:
            msg = "FilesystemDomain wasn't created"
            logger.exception(msg)
            raise RuntimeError(msg)

        await self._stack.aclose()

    def mcp_servers(self) -> Sequence[MCPServerStdio]:
        """Return MCP filesystem server configuration."""
        return [
            MCPServerStdio(
                "docker",
                [
                    "run",
                    "-i",
                    "--rm",
                    "--mount",
                    f"type=bind,src={self._tmp_dir},dst=/projects",
                    "mcp/filesystem",
                    "/projects",
                ],
            )
        ]

    def tasks(self) -> Sequence[MusicReportTask | DuplicatesSearchingTask]:
        """Return all filesystem tasks."""
        return [MusicReportTask(self._tmp_dir), DuplicatesSearchingTask(self._tmp_dir)]
