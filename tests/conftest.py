"""Shared fixtures and mocks for tests."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from types import TracebackType
from typing import Any, Self
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.agent import Agent
from pydantic_ai.mcp import MCPServer
from pydantic_ai.run import AgentRunResult
from pydantic_ai.toolsets import CombinedToolset
from pydantic_evals.evaluators import Evaluator

from mcp_evals.domain import Domain
from mcp_evals.secrets import DomainSecrets, TaskSecrets
from mcp_evals.task import Task


@pytest.fixture
def mock_agent() -> Agent[Any, Any]:
    """Create a mock Agent with async run method."""
    agent = MagicMock(spec=Agent)
    agent.run = AsyncMock(return_value=MagicMock(spec=AgentRunResult))
    return agent


@pytest.fixture
def mock_toolset() -> CombinedToolset:
    """Create a mock CombinedToolset with async context manager behavior."""
    toolset = MagicMock(spec=CombinedToolset)

    @asynccontextmanager
    async def mock_context() -> AsyncIterator[CombinedToolset]:
        yield toolset

    toolset.__aenter__ = AsyncMock(return_value=toolset)
    toolset.__aexit__ = AsyncMock(return_value=None)
    return toolset


@pytest.fixture
def mock_mcp_server() -> MCPServer:
    """Create a mock MCPServer."""
    return MagicMock(spec=MCPServer)


@pytest.fixture
def mock_evaluator() -> Evaluator[Task[TaskSecrets, Any], AgentRunResult]:
    """Create a mock Evaluator."""
    evaluator = MagicMock(spec=Evaluator)
    evaluator.evaluate = AsyncMock(return_value=1.0)
    return evaluator


class MockTask(Task[TaskSecrets, str]):
    """Mock Task implementation for testing."""

    name = "mock_task"
    goal = "Mock task goal"
    evaluators: tuple[Evaluator[Task[TaskSecrets, str], AgentRunResult], ...] = ()

    def __init__(
        self,
        name: str = "mock_task",
        goal: str = "Mock task goal",
        evaluators: tuple[Evaluator[Task[TaskSecrets, str], AgentRunResult], ...] | None = None,
        setup_called: list[bool] | None = None,
        teardown_called: list[bool] | None = None,
    ) -> None:
        self.name = name
        self.goal = goal
        self.evaluators = evaluators or ()
        self._setup_called = setup_called or []
        self._teardown_called = teardown_called or []

    async def setup(self, stack: AsyncExitStack[Any]) -> None:  # noqa: ARG002
        """Track that setup was called."""
        self._setup_called.append(True)

    async def teardown(self) -> None:
        """Track that teardown was called."""
        self._teardown_called.append(True)


class MockDomain(Domain[DomainSecrets]):
    """Mock Domain implementation for testing."""

    name = "mock_domain"

    def __init__(
        self,
        name: str = "mock_domain",
        mcp_servers: list[MCPServer] | None = None,
        tasks: list[Task[TaskSecrets, Any]] | None = None,
        toolset: CombinedToolset | None = None,
        setup_called: list[bool] | None = None,
        teardown_called: list[bool] | None = None,
    ) -> None:
        self.name = name
        self._mcp_servers = mcp_servers or []
        self._tasks = tasks or []
        self._mock_toolset = toolset
        self._toolset = None  # Initialize _toolset to match parent class
        self._setup_called = setup_called or []
        self._teardown_called = teardown_called or []

    def mcp_servers(self) -> list[MCPServer]:
        """Return mock MCP servers."""
        return self._mcp_servers

    def tasks(self) -> list[Task[TaskSecrets, Any]]:
        """Return mock tasks."""
        return self._tasks

    async def setup(self, stack: AsyncExitStack[Any]) -> None:  # noqa: ARG002
        """Track that setup was called."""
        self._setup_called.append(True)

    async def teardown(self) -> None:
        """Track that teardown was called."""
        self._teardown_called.append(True)

    async def __aenter__(self) -> Self:
        """Enter context with optional mock toolset."""
        if self._mock_toolset is not None:
            # Use provided mock toolset
            async with AsyncExitStack() as stack:
                await self.setup(stack)
                self._stack = stack.pop_all()
            self._toolset = self._mock_toolset
            if self._toolset is not None:
                await self._toolset.__aenter__()
            return self
        # Use parent implementation
        return await super().__aenter__()

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool | None:
        """Exit context with optional mock toolset."""
        if self._mock_toolset is not None:
            # Use provided mock toolset
            if self._toolset is not None:
                await self._toolset.__aexit__(exc_type, exc_val, exc_tb)
            if self._stack is not None:
                await self._stack.aclose()
                self._stack = None
            await self.teardown()
            return None
        # Use parent implementation
        return await super().__aexit__(exc_type, exc_val, exc_tb)
