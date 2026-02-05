"""Evaluator that checks a column exists on a table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class ColumnExists(Evaluator["PostgresTask", AgentRunResult]):
    """Check that the given column exists on the table."""

    table: str
    column: str
    schema: str = "public"

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Query information_schema.columns; return 1.0 if column exists."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
                """,
                (self.schema, self.table, self.column),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Column {self.schema}.{self.table}.{self.column} does not exist",
                )
        return 1.0
