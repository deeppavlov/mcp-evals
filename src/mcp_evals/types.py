"""Public type aliases for mcp_evals."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from enum import StrEnum
from typing import Any

from pydantic_ai import AgentRunResult

from mcp_evals.task import Task

type DepsMaker = Callable[[Task[Any, Any]], AbstractAsyncContextManager[object]]

type TrainingTestingCallback = Callable[[], Awaitable[None]]

type EvaluatedFn = (
    Callable[[Task[Any, Any]], Awaitable[AgentRunResult[Any]]] | Callable[[Task[Any, Any]], AgentRunResult[Any]]
)

type RunResultProcessor = Callable[[Task[Any, Any], AgentRunResult[Any], object], Awaitable[None]]


class Runner(StrEnum):
    """Different running strategies implemented in mcp_evals."""

    INFERENCE_ONLY = "INFERENCE_ONLY"
    HOLD_OUT = "HOLD_OUT"
    CROSS_VALIDATION = "CROSS_VALIDATION"
    SELF_CORRECTION = "SELF_CORRECTION"
