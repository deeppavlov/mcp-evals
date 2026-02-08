"""Evaluator that checks a table has the expected set of columns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class TableColumnsMatch(Evaluator["PostgresTask", AgentRunResult]):
    """Check that the table has exactly the expected columns (order-insensitive set match)."""

    table: str
    expected_columns: list[str]
    schema: str = "public"
    allow_extra: bool = False

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Query information_schema.columns; compare to expected_columns."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY column_name
                """,
                (self.schema, self.table),
            )
            actual = {row[0] for row in await cur.fetchall()}
        expected = set(self.expected_columns)
        missing = expected - actual
        extra = actual - expected
        if missing:
            return EvaluationReason(
                value=0.0,
                reason=f"Table {self.schema}.{self.table} missing columns: {sorted(missing)}",
            )
        if not self.allow_extra and extra:
            return EvaluationReason(
                value=0.0,
                reason=f"Table {self.schema}.{self.table} has unexpected columns: {sorted(extra)}",
            )
        return 1.0
