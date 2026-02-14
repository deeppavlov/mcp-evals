"""Tests for custom deps passed to pydantic_ai agent.run."""

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
async def test_run_agent_on_task_passes_deps_to_agent_run() -> None:
    """run_agent_on_task forwards deps to agent.run()."""
    mock_result = MagicMock(spec=AgentRunResult)
    mock_agent = MagicMock(spec=Agent)
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_toolset = MagicMock(spec=CombinedToolset)
    task = _SimpleTask()
    custom_deps = {"key": "value"}

    result = await run_agent_on_task(task, agent=mock_agent, toolset=mock_toolset, deps=custom_deps)

    assert result is mock_result
    mock_agent.run.assert_called_once()
    call_kw = mock_agent.run.call_args.kwargs
    assert call_kw.get("deps") is custom_deps


@pytest.mark.asyncio
async def test_run_agent_on_task_with_none_deps() -> None:
    """run_agent_on_task with deps=None passes None to agent.run()."""
    mock_result = MagicMock(spec=AgentRunResult)
    mock_agent = MagicMock(spec=Agent)
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_toolset = MagicMock(spec=CombinedToolset)
    task = _SimpleTask()

    await run_agent_on_task(task, agent=mock_agent, toolset=mock_toolset, deps=None)

    call_kw = mock_agent.run.call_args.kwargs
    assert call_kw.get("deps") is None
