"""Tests for deps_lifecycle passed to pydantic_ai agent.run."""

from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Self
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.agent import Agent
from pydantic_ai.run import AgentRunResult
from pydantic_ai.toolsets import CombinedToolset
from pydantic_evals.evaluators import Evaluator

from mcp_evals._internal.evaluated_fn import run_agent_on_task
from mcp_evals.secrets import TaskSecrets
from mcp_evals.task import Task


class _SimpleTask(Task[TaskSecrets, str]):
    """Minimal task for testing."""

    name = "simple"
    goal = "Do something"
    evaluators: tuple[Evaluator[Self, AgentRunResult], ...] = ()
    output_type = str
    secrets_type = TaskSecrets

    def __init__(self) -> None:
        pass


@pytest.mark.asyncio
async def test_run_agent_on_task_uses_deps_lifecycle_and_passes_yielded_deps_to_agent_run() -> None:
    """run_agent_on_task enters deps_lifecycle() CM and passes yielded value to agent.run()."""
    mock_result = MagicMock(spec=AgentRunResult)
    mock_agent = MagicMock(spec=Agent)
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_toolset = MagicMock(spec=CombinedToolset)
    task = _SimpleTask()
    custom_deps = {"key": "value"}

    enter_called = []
    exit_called = []

    @asynccontextmanager
    async def mock_cm() -> AsyncGenerator[object]:
        enter_called.append(1)
        try:
            yield custom_deps
        finally:
            exit_called.append(1)

    def deps_lifecycle() -> AbstractAsyncContextManager[object]:
        return mock_cm()

    result = await run_agent_on_task(task, agent=mock_agent, toolset=mock_toolset, deps_lifecycle=deps_lifecycle)

    assert result is mock_result
    mock_agent.run.assert_called_once()
    call_kw = mock_agent.run.call_args.kwargs
    assert call_kw.get("deps") is custom_deps
    assert len(enter_called) == 1
    assert len(exit_called) == 1


@pytest.mark.asyncio
async def test_run_agent_on_task_with_deps_lifecycle_yielding_none() -> None:
    """run_agent_on_task with deps_lifecycle yielding None passes None to agent.run()."""
    mock_result = MagicMock(spec=AgentRunResult)
    mock_agent = MagicMock(spec=Agent)
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_toolset = MagicMock(spec=CombinedToolset)
    task = _SimpleTask()

    @asynccontextmanager
    async def mock_cm() -> AsyncGenerator[None]:
        yield None

    def deps_lifecycle() -> AbstractAsyncContextManager[None]:
        return mock_cm()

    await run_agent_on_task(task, agent=mock_agent, toolset=mock_toolset, deps_lifecycle=deps_lifecycle)

    call_kw = mock_agent.run.call_args.kwargs
    assert call_kw.get("deps") is None
