"""Tests for deps_maker passed to pydantic_ai agent.run."""

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

    def __init__(self, tool_retries: int = 1) -> None:
        super().__init__(tool_retries=tool_retries)


@pytest.mark.asyncio
async def test_run_agent_on_task_uses_deps_maker_and_passes_yielded_deps_to_agent_run() -> None:
    """run_agent_on_task enters deps_maker() CM and passes yielded value to agent.run()."""
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

    def deps_maker(t: Task[TaskSecrets, str]) -> AbstractAsyncContextManager[object]:
        assert t is task
        return mock_cm()

    result = await run_agent_on_task(task, agent=mock_agent, toolset=mock_toolset, deps_maker=deps_maker)

    assert result is mock_result
    mock_agent.run.assert_called_once()
    call_kw = mock_agent.run.call_args.kwargs
    assert call_kw.get("deps") is custom_deps
    assert len(enter_called) == 1
    assert len(exit_called) == 1


@pytest.mark.asyncio
async def test_run_agent_on_task_with_deps_maker_yielding_none() -> None:
    """run_agent_on_task with deps_maker yielding None passes None to agent.run()."""
    mock_result = MagicMock(spec=AgentRunResult)
    mock_agent = MagicMock(spec=Agent)
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_toolset = MagicMock(spec=CombinedToolset)
    task = _SimpleTask()

    @asynccontextmanager
    async def mock_cm() -> AsyncGenerator[None]:
        yield None

    def deps_maker(t: Task[TaskSecrets, str]) -> AbstractAsyncContextManager[None]:
        assert t is task
        return mock_cm()

    await run_agent_on_task(task, agent=mock_agent, toolset=mock_toolset, deps_maker=deps_maker)

    call_kw = mock_agent.run.call_args.kwargs
    assert call_kw.get("deps") is None


@pytest.mark.asyncio
async def test_run_agent_on_task_invokes_run_result_processor_after_run() -> None:
    """run_agent_on_task calls run_result_processor(task, result, deps) after agent.run()."""
    mock_result = MagicMock(spec=AgentRunResult)
    mock_agent = MagicMock(spec=Agent)
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_toolset = MagicMock(spec=CombinedToolset)
    task = _SimpleTask()
    custom_deps = object()

    processed: list[tuple[Task[TaskSecrets, str], AgentRunResult, object]] = []

    async def run_result_processor(t: Task[TaskSecrets, str], r: AgentRunResult, d: object) -> None:
        processed.append((t, r, d))

    @asynccontextmanager
    async def mock_cm() -> AsyncGenerator[object]:
        yield custom_deps

    def deps_maker(t: Task[TaskSecrets, str]) -> AbstractAsyncContextManager[object]:  # noqa: ARG001
        return mock_cm()

    result = await run_agent_on_task(
        task,
        agent=mock_agent,
        toolset=mock_toolset,
        deps_maker=deps_maker,
        run_result_processor=run_result_processor,
    )

    assert result is mock_result
    assert len(processed) == 1
    proc_task, proc_result, proc_deps = processed[0]
    assert proc_task is task
    assert proc_result is mock_result
    assert proc_deps is custom_deps
