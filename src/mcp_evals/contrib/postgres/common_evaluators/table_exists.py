"""Evaluator that checks a table exists in the schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class TableExists(Evaluator["PostgresTask", AgentRunResult]):
    """Check that the given table exists in the schema."""

    table: str
    schema: str = "public"

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Query information_schema.tables; return 1.0 if table exists."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
                """,
                (self.schema, self.table),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Table {self.schema}.{self.table} does not exist",
                )
        return 1.0
