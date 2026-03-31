"""Public type aliases for mcp_evals."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, TypedDict

from pydantic_ai import AgentRunResult

from mcp_evals.task import Task

type DepsMaker = Callable[[Task[Any, Any]], AbstractAsyncContextManager[object]]


class RunContext(TypedDict):
    """Runner context passed to phase callbacks."""

    phase_to_tasks: dict[str, list[Task[Any, Any]]]


# Callback may accept either only phase_name, or phase_name with run context.
type TrainingTestingCallback = Callable[[str], Awaitable[None]] | Callable[[str, RunContext], Awaitable[None]]

type EvaluatedFn = (
    Callable[[Task[Any, Any]], Awaitable[AgentRunResult[Any]]] | Callable[[Task[Any, Any]], AgentRunResult[Any]]
)

type RunResultProcessor = Callable[[Task[Any, Any], AgentRunResult[Any], object], Awaitable[None]]
