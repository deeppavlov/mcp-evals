"""Trigger and procedure scenario: procedure exists, trigger exists/fires, downstream state correct."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.postgres.safe_execute import AgentSqlError, safe_execute

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class TriggerAndProcedureScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify procedure exists, trigger exists, and optional state checks (counts/rows)."""

    procedure_schema: str
    procedure_name: str
    trigger_schema: str
    trigger_name: str
    support_table_schema: str = "employees"
    support_table_name: str = "salary_alerts"
    state_checks: list[tuple[str, Any]] | None = None
    """Optional list of (query, expected_value) for scalar or (query, expected_row) for one row."""

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Check procedure, trigger, support table; run state_checks if provided."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1 FROM information_schema.routines
                WHERE routine_schema = %s AND routine_name = %s AND routine_type = 'FUNCTION'
                """,
                (self.procedure_schema, self.procedure_name),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Procedure {self.procedure_schema}.{self.procedure_name} not found",
                )
            await cur.execute(
                """
                SELECT 1 FROM information_schema.triggers
                WHERE trigger_schema = %s AND trigger_name = %s
                """,
                (self.trigger_schema, self.trigger_name),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Trigger {self.trigger_schema}.{self.trigger_name} not found",
                )
            await cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
                """,
                (self.support_table_schema, self.support_table_name),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Support table {self.support_table_schema}.{self.support_table_name} not found",
                )
            if self.state_checks:
                for query, expected in self.state_checks:
                    try:
                        await safe_execute(cur, query)
                    except AgentSqlError as e:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"State check failed: {e.cause}",
                        )
                    row = await cur.fetchone()
                    if row is None:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"State check returned no row: {query[:80]}...",
                        )
                    actual = row[0] if len(row) == 1 else tuple(row)
                    if actual != expected:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"State check failed: got {actual}, expected {expected}",
                        )
        return 1.0
