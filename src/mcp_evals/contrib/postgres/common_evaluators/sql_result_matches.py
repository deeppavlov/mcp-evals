"""Evaluator that compares query results to expected rows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp_evals.contrib.postgres.task import PostgresTask

FLOAT_TOLERANCE = 0.1


def default_rows_match(actual: tuple[Any, ...], expected: tuple[Any, ...]) -> bool:
    """Compare rows with tolerance for Decimal and date types."""
    if len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected, strict=True):
        if isinstance(a, Decimal) and isinstance(e, (Decimal, float, int)):
            if abs(float(a) - float(e)) > FLOAT_TOLERANCE:
                return False
        elif hasattr(a, "strftime") and hasattr(e, "strftime"):
            if str(a) != str(e):
                return False
        elif a != e:
            return False
    return True


@dataclass
class SqlResultMatches(Evaluator["PostgresTask", AgentRunResult]):
    """Run a query and compare results to expected rows or to another query's result."""

    query: str
    expected_rows: list[tuple[Any, ...]] | None = None
    expected_query: str | None = None
    rows_match_fn: Callable[[tuple[Any, ...], tuple[Any, ...]], bool] = default_rows_match

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Execute query; compare to expected_rows or to result of expected_query."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(self.query)
            actual_rows = await cur.fetchall()
        if self.expected_query is not None:
            async with await psycopg.AsyncConnection.connect(**params) as conn2, conn2.cursor() as cur2:
                await cur2.execute(self.expected_query)
                expected_rows = await cur2.fetchall()
        else:
            expected_rows = self.expected_rows or []
        if len(actual_rows) != len(expected_rows):
            return EvaluationReason(
                value=0.0,
                reason=f"Row count mismatch: got {len(actual_rows)}, expected {len(expected_rows)}",
            )
        for i, (actual, expected) in enumerate(zip(actual_rows, expected_rows, strict=True)):
            if not self.rows_match_fn(tuple(actual), tuple(expected)):
                return EvaluationReason(
                    value=0.0,
                    reason=f"Row {i} mismatch: got {actual}, expected {expected}",
                )
        return 1.0
