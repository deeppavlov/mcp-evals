"""Deferred constraint scenario: invalid op blocked, deferred allows valid coordinated update."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from psycopg import sql
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class DeferredConstraintScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify deferred constraints: immediate violation fails; deferred + coordinated update succeeds."""

    failing_sql: str
    """SQL that should fail without deferral (e.g. violates FK or check)."""
    deferred_sql_blocks: list[str]
    """List of SQL statements run in one transaction after SET CONSTRAINTS ... DEFERRED."""
    constraint_names: list[str] | None = None
    """If set, use SET CONSTRAINTS name DEFERRED; else use SET CONSTRAINTS ALL DEFERRED."""

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Run failing_sql (expect failure); then run deferred block in a transaction (expect success)."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            try:
                await cur.execute(self.failing_sql)
                return EvaluationReason(
                    value=0.0,
                    reason="Expected failing_sql to raise; it succeeded",
                )
            except psycopg.Error:
                await conn.rollback()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await conn.set_autocommit(False)
            try:
                if self.constraint_names:
                    for name in self.constraint_names:
                        await cur.execute(sql.SQL("SET CONSTRAINTS {} DEFERRED").format(sql.Identifier(name)))
                else:
                    await cur.execute("SET CONSTRAINTS ALL DEFERRED")
                for block in self.deferred_sql_blocks:
                    await cur.execute(block)
                await conn.commit()
            except psycopg.Error:
                await conn.rollback()
                raise
        return 1.0
