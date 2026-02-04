"""Base class for all filesystem tasks."""

from contextlib import AsyncExitStack
from pathlib import Path

from mcp_evals.contrib.filesystem.utils import Fixture, download_fixture, prepare_workspace
from mcp_evals.secrets import TaskSecrets
from mcp_evals.task import Task


class FilesystemTask(Task[TaskSecrets]):
    """Base class for all filesystem tasks."""

    _stack: AsyncExitStack | None = None

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Init."""
        super().__init__()

        self.work_dir = work_dir
        self.fixture = fixture

    async def setup(self) -> None:
        """Set up the task environment."""
        if self._stack is not None:
            msg = f"Task {self.name} context already entered"
            raise RuntimeError(msg)

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        # Download fixture
        fixture_path = await download_fixture(self.fixture)

        # Create isolated workspace - enter context manager into stack
        workspace_ctx = prepare_workspace(fixture_path, self.work_dir)
        await self._stack.enter_async_context(workspace_ctx)

    async def teardown(self) -> None:
        """Clean up the task environment."""
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
