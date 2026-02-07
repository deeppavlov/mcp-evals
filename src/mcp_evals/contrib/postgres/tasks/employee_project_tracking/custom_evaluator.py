"""Project tracking relationship scenario: tables, columns, indexes, relationship correctness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from psycopg import AsyncCursor
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class ProjectTrackingRelationshipScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify required tables exist, required columns and indexes, and optional relationship checks."""

    required_tables: list[str]
    table_columns: list[tuple[str, list[str]]]
    """(table, [col1, col2]) for each table that must have these columns."""
    index_specs: list[tuple[str, str] | tuple[str, list[str]]]
    """Same as IndexesExist.index_specs."""
    schema: str = "public"
    relationship_queries: list[tuple[str, int]] | None = None
    """(query, expected_count) to assert relationship/count invariants."""

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Check tables, columns, indexes; run relationship queries."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            fail = await _check_tables(cur, self.required_tables, self.schema)
            if fail is not None:
                return fail
            fail = await _check_table_columns(cur, self.table_columns, self.schema)
            if fail is not None:
                return fail
            fail = await _check_index_specs(cur, self.index_specs, self.schema)
            if fail is not None:
                return fail
            if self.relationship_queries:
                fail = await _check_relationship_queries(cur, self.relationship_queries)
                if fail is not None:
                    return fail
        return 1.0


async def _check_tables(cur: AsyncCursor, tables: list[str], schema: str) -> EvaluatorOutput | None:
    for table in tables:
        await cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            (schema, table),
        )
        if await cur.fetchone() is None:
            return EvaluationReason(value=0.0, reason=f"Table {schema}.{table} not found")
    return None


async def _check_table_columns(
    cur: AsyncCursor,
    table_columns: list[tuple[str, list[str]]],
    schema: str,
) -> EvaluatorOutput | None:
    for table, cols in table_columns:
        await cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            """,
            (schema, table),
        )
        actual = {r[0] for r in await cur.fetchall()}
        for col in cols:
            if col not in actual:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Column {schema}.{table}.{col} not found",
                )
    return None


async def _check_index_specs(
    cur: AsyncCursor,
    index_specs: list[tuple[str, str] | tuple[str, list[str]]],
    schema: str,
) -> EvaluatorOutput | None:
    for spec in index_specs:
        table, column_or_cols = spec
        if isinstance(column_or_cols, str):
            await cur.execute(
                """
                SELECT 1 FROM pg_indexes
                WHERE schemaname = %s AND tablename = %s AND indexdef LIKE %s
                """,
                (schema, table, f"%{column_or_cols}%"),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"No index on {table}.{column_or_cols}",
                )
        else:
            await cur.execute(
                "SELECT indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = %s",
                (schema, table),
            )
            indexdefs = [r[0] for r in await cur.fetchall()]
            if not any(all(c in (idx or "") for c in column_or_cols) for idx in indexdefs):
                return EvaluationReason(
                    value=0.0,
                    reason=f"No index on {table} covering {column_or_cols}",
                )
    return None


async def _check_relationship_queries(
    cur: AsyncCursor,
    relationship_queries: list[tuple[str, int]],
) -> EvaluatorOutput | None:
    for query, expected_count in relationship_queries:
        await cur.execute(query)
        row = await cur.fetchone()
        count = row[0] if row else 0
        if count != expected_count:
            return EvaluationReason(
                value=0.0,
                reason=f"Relationship check: expected count {expected_count}, got {count}",
            )
    return None
