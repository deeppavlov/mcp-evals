"""Hierarchy and assignment scenario: multi-table relationship and column/row checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


class _AsyncCursorLike(Protocol):
    """Protocol for psycopg async cursor used in helpers."""

    async def execute(self, query: str, params: tuple[object, ...] | None = ...) -> None: ...
    async def fetchone(self) -> object | None: ...
    async def fetchall(self) -> list[object]: ...


@dataclass
class HierarchyAndAssignmentScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify tables/columns exist and optional list of (query, expected_scalar_or_row) checks."""

    required_tables: list[str]
    schema: str = "public"
    required_columns: list[tuple[str, list[str]]] | None = None
    """List of (table, [col1, col2])."""
    scalar_checks: list[tuple[str, Any]] | None = None
    """(query, expected_value)."""
    row_checks: list[tuple[str, tuple[Any, ...]]] | None = None
    """(query, expected_row)."""

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Check tables and columns; run scalar and row checks."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            fail = await _check_tables(cur, self.required_tables, self.schema)
            if fail is not None:
                return fail
            if self.required_columns:
                fail = await _check_columns(cur, self.required_columns, self.schema)
                if fail is not None:
                    return fail
            if self.scalar_checks:
                fail = await _check_scalars(cur, self.scalar_checks)
                if fail is not None:
                    return fail
            if self.row_checks:
                fail = await _check_rows(cur, self.row_checks)
                if fail is not None:
                    return fail
        return 1.0


async def _check_tables(
    cur: _AsyncCursorLike, tables: list[str], schema: str
) -> EvaluatorOutput | None:
    """Return EvaluationReason if any table missing, else None."""
    for table in tables:
        await cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            (schema, table),
        )
        if await cur.fetchone() is None:
            return EvaluationReason(value=0.0, reason=f"Table {schema}.{table} not found")
    return None


async def _check_columns(
    cur: _AsyncCursorLike,
    table_columns: list[tuple[str, list[str]]],
    schema: str,
) -> EvaluatorOutput | None:
    """Return EvaluationReason if any column missing, else None."""
    for table, cols in table_columns:
        await cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            """,
            (schema, table),
        )
        actual_cols: set[str] = {r[0] for r in await cur.fetchall()}
        for col in cols:
            if col not in actual_cols:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Column {schema}.{table}.{col} not found",
                )
    return None


async def _check_scalars(
    cur: _AsyncCursorLike,
    checks: list[tuple[str, Any]],
) -> EvaluatorOutput | None:
    """Return EvaluationReason if any scalar check fails, else None."""
    for query, expected in checks:
        await cur.execute(query)
        row = await cur.fetchone()
        if row is None:
            return EvaluationReason(value=0.0, reason=f"Check returned no row: {query[:60]}...")
        scalar_val: Any = row[0] if len(row) == 1 else tuple(row)
        if scalar_val != expected:
            return EvaluationReason(
                value=0.0,
                reason=f"Check failed: got {scalar_val}, expected {expected}",
            )
    return None


async def _check_rows(
    cur: _AsyncCursorLike,
    checks: list[tuple[str, tuple[Any, ...]]],
) -> EvaluatorOutput | None:
    """Return EvaluationReason if any row check fails, else None."""
    for query, expected_row in checks:
        await cur.execute(query)
        rows = await cur.fetchall()
        if len(rows) != 1:
            return EvaluationReason(
                value=0.0,
                reason=f"Row check expected 1 row, got {len(rows)}",
            )
        row_val: tuple[Any, ...] = tuple(rows[0])
        if row_val != expected_row:
            return EvaluationReason(
                value=0.0,
                reason=f"Row mismatch: got {row_val}, expected {expected_row}",
            )
    return None
