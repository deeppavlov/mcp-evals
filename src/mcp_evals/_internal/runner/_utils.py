"""Internal runner for executing domains and tasks."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from pydantic_ai.run import AgentRunResult
from pydantic_evals import Case

from mcp_evals.domain import Domain
from mcp_evals.task import Task
from mcp_evals.types import DepsMaker


@asynccontextmanager
async def _no_deps_cm() -> AsyncIterator[None]:
    yield None


def default_deps_maker() -> DepsMaker:
    """Default deps maker used when user does not pass one (yields None)."""
    return lambda _task: _no_deps_cm()


def task_lifecycle(
    domain: Domain[Any],
    scope: str = "default",
) -> Callable[[Case[Task[Any, Any], AgentRunResult, None]], Any]:
    """Return a case context manager that wraps task execution + evaluation and records checkpoint on success.

    The returned callable is used as case_context_manager for dataset.evaluate().
    On normal exit (no exception), if domain has a checkpoint, the (scope, task.name) run is recorded.
    """

    @asynccontextmanager
    async def _lifecycle(
        case: Case[Task[Any, Any], AgentRunResult, None],
    ) -> AsyncIterator[None]:
        task = case.inputs  # In mcp_evals, inputs IS the Task instance
        async with task:
            yield
        # Normal exit: record so this run can be skipped on resume
        if domain.checkpoint is not None:
            domain.checkpoint.record_finished(scope, task.name)

    return _lifecycle
