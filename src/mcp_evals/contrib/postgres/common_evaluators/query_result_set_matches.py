"""Evaluator that compares query result sets (order-insensitive)."""

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

from .sql_result_matches import default_rows_match


def _normalize_cell(c: object) -> tuple[float | str | object, ...]:
    """Normalize for set membership (hashable, comparable)."""
    if isinstance(c, Decimal):
        return (float(c),)
    if hasattr(c, "strftime"):
        return (str(c),)
    return (c,)


def _row_to_tuple(row: tuple[Any, ...]) -> tuple[tuple[Any, ...], ...]:
    """Convert row to hashable tuple of normalized cells."""
    return tuple(_normalize_cell(x) for x in row)


@dataclass
class QueryResultSetMatches(Evaluator["PostgresTask", AgentRunResult]):
    """Run two queries and compare result sets (order-insensitive set equality).

    Useful for migration checks where row order is not defined.
    """

    query: str
    expected_query: str | None = None
    expected_rows: list[tuple[Any, ...]] | None = None
    rows_match_fn: Callable[[tuple[Any, ...], tuple[Any, ...]], bool] = default_rows_match

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Execute query; compare result set to expected_query result or expected_rows."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(self.query)
            actual_rows = [tuple(r) for r in await cur.fetchall()]
        if self.expected_query is not None:
            async with await psycopg.AsyncConnection.connect(**params) as conn2, conn2.cursor() as cur2:
                await cur2.execute(self.expected_query)
                expected_rows = [tuple(r) for r in await cur2.fetchall()]
        else:
            expected_rows = list(self.expected_rows or [])
        actual_set = set()
        expected_set = set()
        for r in actual_rows:
            actual_set.add(_row_to_tuple(r))
        for r in expected_rows:
            expected_set.add(_row_to_tuple(r))
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        if missing or extra:
            reasons = []
            if missing:
                reasons.append(f"missing {len(missing)} expected row(s)")
            if extra:
                reasons.append(f"extra {len(extra)} row(s)")
            return EvaluationReason(
                value=0.0,
                reason="; ".join(reasons),
            )
        return 1.0
