"""Evaluator that checks multiple indexes exist on given table columns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class IndexesExist(Evaluator["PostgresTask", AgentRunResult]):
    """Check that all specified indexes exist.

    Each spec is (table, column) or (table, [col1, col2, ...]) for composite indexes.
    For composite, at least one index on the table must have indexdef containing all columns.
    """

    index_specs: list[tuple[str, str] | tuple[str, list[str]]]
    schemaname: str = "public"

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify each index spec; return 1.0 only if all pass."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            for spec in self.index_specs:
                table, column_or_cols = spec
                if isinstance(column_or_cols, str):
                    await cur.execute(
                        """
                        SELECT 1 FROM pg_indexes
                        WHERE schemaname = %s AND tablename = %s AND indexdef LIKE %s
                        """,
                        (self.schemaname, table, f"%{column_or_cols}%"),
                    )
                    if await cur.fetchone() is None:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"No index on {table}.{column_or_cols} found",
                        )
                else:
                    await cur.execute(
                        """
                        SELECT indexdef FROM pg_indexes
                        WHERE schemaname = %s AND tablename = %s
                        """,
                        (self.schemaname, table),
                    )
                    indexdefs = [row[0] for row in await cur.fetchall()]
                    found = any(all(col in (idx or "") for col in column_or_cols) for idx in indexdefs)
                    if not found:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"No index on {table} covering all of {column_or_cols}",
                        )
        return 1.0
