"""Public type aliases for mcp_evals."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from pydantic_ai import AgentRunResult

from mcp_evals.task import Task

type DepsMaker = Callable[[Task[Any, Any]], AbstractAsyncContextManager[object]]

# Callback receives phase_name (e.g. "train_0", "test_0") for idempotent implementations.
type TrainingTestingCallback = Callable[[str], Awaitable[None]]

type EvaluatedFn = (
    Callable[[Task[Any, Any]], Awaitable[AgentRunResult[Any]]] | Callable[[Task[Any, Any]], AgentRunResult[Any]]
)

type RunResultProcessor = Callable[[Task[Any, Any], AgentRunResult[Any], object], Awaitable[None]]
