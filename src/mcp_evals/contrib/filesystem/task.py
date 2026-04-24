"""Base class for all filesystem tasks."""

import os
from collections.abc import Sequence
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai.mcp import MCPServerStdio

from mcp_evals.contrib.filesystem.utils import Fixture, download_fixture, prepare_workspace
from mcp_evals.secrets import TaskSecrets
from mcp_evals.task import GoalFromDescriptionMixin, Task


class FinishTask(BaseModel):
    """Call this tool when done with the task."""

    answer: str | None = Field(None, description="Optional answer")


class FilesystemTask(GoalFromDescriptionMixin, Task[TaskSecrets, FinishTask]):
    """Base class for all filesystem tasks."""

    output_type = FinishTask

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Init."""
        super().__init__(tool_retries=tool_retries)

        self.root_dir = work_dir
        # Per-task workspace (enables safe parallel execution)
        self.work_dir = work_dir / self.name
        self.fixture = fixture

    def mcp_servers(self) -> Sequence[MCPServerStdio]:
        """Return task-scoped MCP filesystem server configuration."""
        # On Linux bind mounts, files created in the container default to root
        # ownership; the host user then cannot delete them in prepare_workspace
        # teardown. Match host UID/GID so cleanup works without sudo.
        docker_args = [
            "run",
            "-i",
            "--rm",
        ]
        if hasattr(os, "getuid"):
            docker_args.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
        docker_args.extend(
            [
                "--mount",
                f"type=bind,src={self.work_dir},dst=/projects",
                "-w",
                "/projects",
                "mcp-filesystem-server:pydantic-ai-mcp-evals",
                "/projects",
            ]
        )
        return [
            MCPServerStdio(
                "docker",
                docker_args,
                max_retries=self.tool_retries,
            )
        ]

    async def setup(self, stack: AsyncExitStack[Any]) -> None:
        """Set up the task environment."""
        # Download fixture
        fixture_path = await download_fixture(self.fixture)

        # Create isolated workspace - enter context manager into stack
        workspace_ctx = prepare_workspace(fixture_path, self.work_dir)
        await stack.enter_async_context(workspace_ctx)
