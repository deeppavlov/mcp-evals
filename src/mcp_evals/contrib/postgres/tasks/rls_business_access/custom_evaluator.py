"""RLS scenario evaluator: role/user-context switching and behavioral assertions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import psycopg
from psycopg import AsyncCursor
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
    content_visibility: tuple[str, str, int, int] | None = None
    """If set, (alice_id, eve_id, alice_min_posts, eve_min_posts) for Test 7: content visibility by user."""
    anonymous_user_check: bool = False
    """If True, run Test 8: anonymous sees only public users (anon count == public count, anon > 0)."""

    async def _check_content_visibility(self, cur: AsyncCursor[Any]) -> EvaluationReason | None:
        """Test 7: content visibility differs by user (alice vs eve post counts). Returns failure reason or None."""
        if self.content_visibility is None:
            return None
        alice_id, eve_id, alice_min, eve_min = self.content_visibility
        await cur.execute("SET app.current_user_id = %s", (alice_id,))
        await cur.execute("SELECT COUNT(*) FROM posts")
        row = await cur.fetchone()
        alice_count = row[0] if row is not None else 0
        await cur.execute("SET app.current_user_id = %s", (eve_id,))
        await cur.execute("SELECT COUNT(*) FROM posts")
        row = await cur.fetchone()
        eve_count = row[0] if row is not None else 0
        if alice_count < alice_min or eve_count < eve_min:
            return EvaluationReason(
                value=0.0,
                reason=(
                    f"Content visibility: expected alice>={alice_min}, eve>={eve_min}; "
                    f"got alice={alice_count}, eve={eve_count}"
                ),
            )
        return None

    async def _check_anonymous_user(self, cur: AsyncCursor[Any]) -> EvaluationReason | None:
        """Test 8: anonymous user sees only public profiles. Returns failure reason or None."""
        if not self.anonymous_user_check:
            return None
        await cur.execute("SET app.current_user_id = ''")
        await cur.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        anon_count = row[0] if row is not None else 0
        await cur.execute("SELECT COUNT(*) FROM users WHERE is_public = true")
        row = await cur.fetchone()
        public_count = row[0] if row is not None else 0
        if anon_count != public_count or anon_count <= 0:
            return EvaluationReason(
                value=0.0,
                reason=(
                    f"Anonymous user: expected anon==public and anon>0; "
                    f"got anon={anon_count}, public={public_count}"
                ),
            )
        return None

    async def _check_tables_rls(self, cur: AsyncCursor[Any]) -> EvaluationReason | None:
        """Verify RLS is enabled on all configured tables. Returns failure reason or None."""
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
        return None

    async def _run_assertions(self, cur: AsyncCursor[Any]) -> EvaluationReason | None:
        """Run all RLS behavioral assertions. Returns failure reason or None."""
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
        return None

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
            for step in (self._check_tables_rls, self._run_assertions):
                fail = await step(cur)
                if fail is not None:
                    return fail
            for check in (self._check_content_visibility, self._check_anonymous_user):
                fail = await check(cur)
                if fail is not None:
                    return fail
        return 1.0
