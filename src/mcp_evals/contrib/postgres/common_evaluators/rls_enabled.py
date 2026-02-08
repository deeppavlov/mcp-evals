"""Evaluator that checks Row-Level Security is enabled on a table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class RlsEnabled(Evaluator["PostgresTask", AgentRunResult]):
    """Check that RLS (relrowsecurity) is enabled on the given table(s)."""

    tables: list[str]
    schema: str = "public"

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Query pg_class for relrowsecurity; return 1.0 only if all tables have RLS on."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            for table in self.tables:
                await cur.execute(
                    """
                    SELECT relrowsecurity FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = %s AND c.relname = %s
                    """,
                    (self.schema, table),
                )
                row = await cur.fetchone()
                if row is None:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Table {self.schema}.{table} not found",
                    )
                if not row[0]:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"RLS is not enabled on table {self.schema}.{table}",
                    )
        return 1.0
