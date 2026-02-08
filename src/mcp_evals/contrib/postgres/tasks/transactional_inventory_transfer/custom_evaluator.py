"""Transactional function scenario: transfer function + audit log and error-path checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from psycopg import sql
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.postgres.safe_execute import AgentSqlError, safe_execute

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class TransferSuccessCase:
    """One successful transfer to verify: call function, check quantities and audit."""

    source_id: int
    target_id: int
    part_num: str
    color_id: int
    quantity: int
    reason: str
    get_quantity_sql: str = (
        "SELECT quantity FROM public.lego_inventory_parts WHERE inventory_id = %s AND part_num = %s AND color_id = %s"
    )


@dataclass
class TransactionalFunctionScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify transfer function exists, audit table exists, then run success case(s)."""

    function_name: str
    audit_table: str
    success_cases: list[TransferSuccessCase]
    call_sql: str = "SELECT transfer_parts(%s, %s, %s, %s, %s, %s)"
    schema: str = "public"

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:  # noqa: PLR0911
        """Check function and audit table exist; run one success case and verify quantities + audit."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1 FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname = %s AND p.proname = %s
                """,
                (self.schema, self.function_name),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Function {self.schema}.{self.function_name} does not exist",
                )
            await cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
                """,
                (self.schema, self.audit_table),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Audit table {self.schema}.{self.audit_table} does not exist",
                )
        for case in self.success_cases:
            async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
                await cur.execute(
                    case.get_quantity_sql,
                    (case.source_id, case.part_num, case.color_id),
                )
                source_before = (await cur.fetchone() or (0,))[0]
                await cur.execute(
                    case.get_quantity_sql,
                    (case.target_id, case.part_num, case.color_id),
                )
                target_before = (await cur.fetchone() or (0,))[0]
                await cur.execute(
                    sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(self.audit_table)),
                )
                log_count_before = (await cur.fetchone() or (0,))[0]
                try:
                    await safe_execute(
                        cur,
                        self.call_sql,
                        (case.source_id, case.target_id, case.part_num, case.color_id, case.quantity, case.reason),
                    )
                except AgentSqlError as e:
                    return EvaluationReason(value=0.0, reason=f"Function raised: {e.cause}")
                await cur.execute(
                    case.get_quantity_sql,
                    (case.source_id, case.part_num, case.color_id),
                )
                source_after = (await cur.fetchone() or (0,))[0]
                await cur.execute(
                    case.get_quantity_sql,
                    (case.target_id, case.part_num, case.color_id),
                )
                target_after = (await cur.fetchone() or (0,))[0]
                await cur.execute(
                    sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(self.audit_table)),
                )
                log_count_after = (await cur.fetchone() or (0,))[0]
            if source_after != source_before - case.quantity:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Source quantity mismatch: expected {source_before - case.quantity}, got {source_after}",
                )
            if target_after != target_before + case.quantity:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Target quantity mismatch: expected {target_before + case.quantity}, got {target_after}",
                )
            if log_count_after <= log_count_before:
                return EvaluationReason(
                    value=0.0,
                    reason="No new audit log entry after transfer",
                )
        return 1.0
