"""Analysis coverage scenario: analysis table(s) match live catalog, no extra analysis tables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class AnalysisTableSpec:
    """One analysis table to verify: name, expected columns, catalog query to compare (table_name, column_name)."""

    table_name: str
    expected_columns: list[str]
    catalog_query: str
    """Query returning (table_name, column_name) of actual catalog objects to compare against analysis table."""
    analysis_columns_query: str
    """Query returning (table_name, column_name) from the analysis table."""
    schema: str = "public"


@dataclass
class AnalysisCoverageScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify analysis tables exist, have expected columns, and match live catalog; no extra analysis tables."""

    analysis_specs: list[AnalysisTableSpec]
    allowed_analysis_tables: list[str]
    """Exact set of analysis table names allowed; no others in schema."""
    analysis_table_pattern: str | None = None
    """If set, only tables with table_name LIKE this are considered analysis tables (e.g. 'vector_analysis_%%')."""

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """For each spec: table exists, columns match, analysis content matches catalog; then check no extra tables."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            for spec in self.analysis_specs:
                await cur.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    (spec.schema, spec.table_name),
                )
                if await cur.fetchone() is None:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Analysis table {spec.table_name} not found",
                    )
                await cur.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s ORDER BY column_name
                    """,
                    (spec.schema, spec.table_name),
                )
                actual_cols = {r[0] for r in await cur.fetchall()}
                expected = set(spec.expected_columns)
                if expected - actual_cols:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Table {spec.table_name} missing columns: {expected - actual_cols}",
                    )
                await cur.execute(spec.catalog_query)
                catalog_set = {tuple(r) for r in await cur.fetchall()}
                await cur.execute(spec.analysis_columns_query)
                analysis_set = {tuple(r) for r in await cur.fetchall()}
                missing = catalog_set - analysis_set
                extra = analysis_set - catalog_set
                if missing:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Analysis {spec.table_name}: missing catalog entries: {missing}",
                    )
                if extra:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Analysis {spec.table_name}: non-existing entries: {extra}",
                    )
            schema = self.analysis_specs[0].schema if self.analysis_specs else "public"
            if self.analysis_table_pattern is not None:
                await cur.execute(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = %s AND table_type = 'BASE TABLE' AND table_name LIKE %s
                    """,
                    (schema, self.analysis_table_pattern),
                )
                analysis_tables = {r[0] for r in await cur.fetchall()}
                allowed = set(self.allowed_analysis_tables)
                extra_tables = analysis_tables - allowed
                if extra_tables:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Unexpected analysis tables: {extra_tables}",
                    )
        return 1.0
