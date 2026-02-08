"""Safe execution of agent-facing SQL: convert DB errors to evaluation failure, re-raise OperationalError."""

from __future__ import annotations

from typing import TYPE_CHECKING

import psycopg
from pydantic_evals.evaluators import EvaluationReason, EvaluatorOutput

if TYPE_CHECKING:
    from collections.abc import Coroutine, Sequence


class AgentSqlError(Exception):
    """Raised when agent-facing SQL fails with a non-infrastructure DB error."""

    def __init__(self, cause: BaseException) -> None:
        """Store the underlying cause and delegate to Exception."""
        self.cause = cause
        super().__init__(cause)


async def safe_execute(
    cur: psycopg.AsyncCursor,
    query: str,
    params: Sequence[object] | None = None,
) -> None:
    """Execute query on cursor; on DatabaseError re-raise OperationalError, else raise AgentSqlError(cause)."""
    try:
        if params is None:
            await cur.execute(query)
        else:
            await cur.execute(query, params)
    except psycopg.DatabaseError as e:
        if isinstance(e, psycopg.OperationalError):
            raise
        raise AgentSqlError(e) from e


async def run_safe(
    coro: Coroutine[object, object, EvaluatorOutput],
) -> EvaluatorOutput:
    """Await coroutine; on DatabaseError re-raise OperationalError, else return EvaluationReason."""
    try:
        return await coro
    except psycopg.DatabaseError as e:
        if isinstance(e, psycopg.OperationalError):
            raise
        return EvaluationReason(value=0.0, reason=str(e))
