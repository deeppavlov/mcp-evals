"""Evaluator that checks specific rows (by key) match expected values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp_evals.contrib.postgres.task import PostgresTask

from .sql_result_matches import default_rows_match


@dataclass
class RowExactMatch(Evaluator["PostgresTask", AgentRunResult]):
    """Run a query that should return exactly one row and compare to expected.

    Typically used with a WHERE on primary key. If multiple rows match, fails.
    """

    query: str
    expected_row: tuple[Any, ...]
    rows_match_fn: Callable[[tuple[Any, ...], tuple[Any, ...]], bool] = default_rows_match

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Execute query; expect single row matching expected_row."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(self.query)
            rows = await cur.fetchall()
        if len(rows) == 0:
            return EvaluationReason(value=0.0, reason="Query returned no rows")
        if len(rows) > 1:
            return EvaluationReason(
                value=0.0,
                reason=f"Query returned {len(rows)} rows, expected 1",
            )
        actual = tuple(rows[0])
        if not self.rows_match_fn(actual, self.expected_row):
            return EvaluationReason(
                value=0.0,
                reason=f"Row mismatch: got {actual}, expected {self.expected_row}",
            )
        return 1.0
