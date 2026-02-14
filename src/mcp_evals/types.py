"""Public type aliases for mcp_evals."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from enum import StrEnum
from typing import Any

from mcp_evals.task import Task

type DepsMaker = Callable[[Task[Any, Any]], AbstractAsyncContextManager[object]]


class Runner(StrEnum):
    """Different running strategies implemented in mcp_evals."""

    INFERENCE_ONLY = "INFERENCE_ONLY"
    HOLD_OUT = "HOLD_OUT"
    CROSS_VALIDATION = "CROSS_VALIDATION"
