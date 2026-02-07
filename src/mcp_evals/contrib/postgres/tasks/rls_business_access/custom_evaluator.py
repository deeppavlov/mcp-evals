"""RLS scenario evaluator: role/user-context switching and behavioral assertions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class RlsAssertion:
    """Single RLS behavioral check: set context, run SQL, expect success or block."""

    set_session: str
    """SQL to set context (e.g. SET app.current_user_id = '...')."""
    run_sql: str
    """SQL to run (e.g. UPDATE users SET ... WHERE id = '...')."""
    should_affect_rows: bool
    """True if the statement should succeed and affect rows; False if RLS should block (0 rows)."""


@dataclass
class RlsScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify RLS: tables have RLS enabled, then run context-switched assertions."""

    tables_with_rls: list[str]
    """Tables that must have relrowsecurity = true."""
    assertions: list[RlsAssertion]
    """Behavioral checks: set session, run SQL, assert rowcount/block."""
    schema: str = "public"
    rls_test_conn_params: dict[str, Any] | None = None
    """If set, use these connection params instead of task.pg_conn_params() (e.g. to connect as test_user for RLS)."""
    rls_test_user: str | None = None
    """If set with rls_test_password, connect as this user (overrides task.pg_conn_params() user/password)."""
    rls_test_password: str | None = None
    """Password for rls_test_user."""

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Check RLS on tables, then run each assertion in order."""
        task = ctx.inputs
        if self.rls_test_conn_params is not None:
            params = self.rls_test_conn_params
        elif self.rls_test_user is not None and self.rls_test_password is not None:
            params = {**task.pg_conn_params(), "user": self.rls_test_user, "password": self.rls_test_password}
        else:
            params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            for table in self.tables_with_rls:
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
                        reason=f"RLS is not enabled on {self.schema}.{table}",
                    )
            for i, assertion in enumerate(self.assertions):
                await cur.execute(assertion.set_session)
                await cur.execute(assertion.run_sql)
                if assertion.should_affect_rows:
                    if cur.rowcount == 0:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"Assertion {i}: expected rows affected but RLS blocked (0 rows)",
                        )
                elif cur.rowcount != 0:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Assertion {i}: expected RLS to block but {cur.rowcount} row(s) affected",
                    )
        return 1.0
