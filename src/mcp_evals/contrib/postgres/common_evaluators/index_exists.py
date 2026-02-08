"""Evaluator that checks an index exists on a table column."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class IndexExists(Evaluator["PostgresTask", AgentRunResult]):
    """Check that an index exists on the given table that references the given column."""

    table: str
    column: str

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Query pg_indexes; return 1.0 if any index on table references column, else 0.0."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename = %s
                    AND indexdef LIKE %s
                    """,
                (self.table, f"%{self.column}%"),
            )
            rows = await cur.fetchall()
        if not rows:
            return EvaluationReason(
                value=0.0,
                reason=f"No index on {self.table}.{self.column} found",
            )
        return 1.0
