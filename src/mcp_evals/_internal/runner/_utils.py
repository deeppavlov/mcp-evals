"""Internal runner for executing domains and tasks."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from pydantic_ai.run import AgentRunResult
from pydantic_evals import Case

from mcp_evals.task import Task
from mcp_evals.types import DepsMaker


@asynccontextmanager
async def _no_deps_cm() -> AsyncIterator[None]:
    yield None


def default_deps_maker() -> DepsMaker:
    """Default deps maker used when user does not pass one (yields None)."""
    return lambda _task: _no_deps_cm()


@asynccontextmanager
async def task_lifecycle(case: Case[Task[Any, Any], AgentRunResult, None]) -> AsyncIterator[None]:
    """Context manager that wraps task execution + evaluation.

    This ensures the task context (setup/teardown) spans both:
    - Task execution (agent.run)
    - Evaluator execution (evaluator.evaluate)

    This is critical because evaluators often need to check the environment
    state (files, database, etc.) that was set up during task.setup(), and
    this state must remain available until after evaluators complete.
    """
    task = case.inputs  # In mcp_evals, inputs IS the Task instance
    async with task:
        yield
