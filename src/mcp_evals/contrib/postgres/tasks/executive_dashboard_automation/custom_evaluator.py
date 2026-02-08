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


async def _check_procedure(
    cur: psycopg.AsyncCursor[tuple[Any, ...]],
    procedure_schema: str,
    procedure_name: str,
) -> EvaluationReason | None:
    """Return failure reason if procedure is missing."""
    await cur.execute(
        """
        SELECT 1 FROM information_schema.routines
        WHERE routine_schema = %s AND routine_name = %s AND routine_type = 'FUNCTION'
        """,
        (procedure_schema, procedure_name),
    )
    if await cur.fetchone() is None:
        return EvaluationReason(
            value=0.0,
            reason=f"Procedure {procedure_schema}.{procedure_name} not found",
        )
    return None


async def _check_trigger(
    cur: psycopg.AsyncCursor[tuple[Any, ...]],
    trigger_schema: str,
    trigger_name: str,
) -> EvaluationReason | None:
    """Return failure reason if trigger is missing."""
    await cur.execute(
        """
        SELECT 1 FROM information_schema.triggers
        WHERE trigger_schema = %s AND trigger_name = %s
        """,
        (trigger_schema, trigger_name),
    )
    if await cur.fetchone() is None:
        return EvaluationReason(
            value=0.0,
            reason=f"Trigger {trigger_schema}.{trigger_name} not found",
        )
    return None


async def _check_support_table(
    cur: psycopg.AsyncCursor[tuple[Any, ...]],
    support_table_schema: str,
    support_table_name: str,
) -> EvaluationReason | None:
    """Return failure reason if support table is missing."""
    await cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """,
        (support_table_schema, support_table_name),
    )
    if await cur.fetchone() is None:
        return EvaluationReason(
            value=0.0,
            reason=f"Support table {support_table_schema}.{support_table_name} not found",
        )
    return None


async def _run_state_checks(
    cur: psycopg.AsyncCursor[tuple[Any, ...]],
    state_checks: list[tuple[str, Any]],
) -> EvaluationReason | None:
    """Run state_checks; return first failure reason or None."""
    for query, expected in state_checks:
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
    return None


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
        fail: EvaluationReason | None = None
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            fail = await _check_procedure(cur, self.procedure_schema, self.procedure_name)
            if fail is None:
                fail = await _check_trigger(cur, self.trigger_schema, self.trigger_name)
            if fail is None:
                fail = await _check_support_table(cur, self.support_table_schema, self.support_table_name)
            if fail is None and self.state_checks:
                fail = await _run_state_checks(cur, self.state_checks)
        return fail if fail is not None else 1.0
