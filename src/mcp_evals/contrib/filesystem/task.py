"""Base class for all filesystem tasks."""

from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_evals.contrib.filesystem.utils import Fixture, download_fixture, prepare_workspace
from mcp_evals.secrets import TaskSecrets
from mcp_evals.task import Task


class FinishTask(BaseModel):
    """Call this tool when done with the task."""

    answer: str | None = Field(None, description="Optional answer")


class FilesystemTask(Task[TaskSecrets, FinishTask]):
    """Base class for all filesystem tasks."""

    output_type = FinishTask

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Init."""
        super().__init__()

        self.work_dir = work_dir
        self.fixture = fixture

    async def setup(self, stack: AsyncExitStack[Any]) -> None:
        """Set up the task environment."""
        # Download fixture
        fixture_path = await download_fixture(self.fixture)

        # Create isolated workspace - enter context manager into stack
        workspace_ctx = prepare_workspace(fixture_path, self.work_dir)
        await stack.enter_async_context(workspace_ctx)
