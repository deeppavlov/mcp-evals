"""Audit findings scenario: expected findings (dangling users, missing/excessive perms, summary)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import psycopg
from psycopg import sql
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    EvaluatorOutput,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class AuditFindingsScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify audit results/details tables exist and contain expected finding sets."""

    results_table: str = "security_audit_results"
    details_table: str = "security_audit_details"
    expected_dangling_users: set[str] | None = None
    expected_missing_permissions: set[tuple[str, str, str]] | None = None
    """(username, table_name, permission_type)."""
    expected_excessive_permissions: set[tuple[str, str, str]] | None = None
    """(username, table_name, permission_type)."""
    details_columns: tuple[str, ...] = (
        "detail_id",
        "username",
        "issue_type",
        "table_name",
        "permission_type",
        "expected_access",
    )

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Check tables exist, parse details rows, compare to expected sets."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (self.results_table,),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(value=0.0, reason=f"Table {self.results_table} not found")
            await cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                (self.details_table,),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(value=0.0, reason=f"Table {self.details_table} not found")
            await cur.execute(
                sql.SQL("SELECT * FROM {} ORDER BY detail_id").format(sql.Identifier(self.details_table)),
            )
            rows = await cur.fetchall()
        if not rows:
            return EvaluationReason(value=0.0, reason="No findings in details table")
        dangling, missing, excessive = _parse_findings(rows)
        return _compare_findings(
            self.expected_dangling_users,
            self.expected_missing_permissions,
            self.expected_excessive_permissions,
            dangling,
            missing,
            excessive,
        )


DETAIL_ROW_MIN_LEN = 6


def _parse_findings(
    rows: list[tuple[Any, ...]],
) -> tuple[set[str], set[tuple[str, str, str]], set[tuple[str, str, str]]]:
    """Parse detail rows into dangling, missing_permissions, excessive_permissions."""
    dangling: set[str] = set()
    missing: set[tuple[str, str, str]] = set()
    excessive: set[tuple[str, str, str]] = set()
    for row in rows:
        if len(row) < DETAIL_ROW_MIN_LEN:
            continue
        _, username, issue_type, table_name, permission_type, expected_access = row[:DETAIL_ROW_MIN_LEN]
        if issue_type == "DANGLING_USER":
            dangling.add(username)
        elif issue_type == "MISSING_PERMISSION" and expected_access and table_name and permission_type:
            missing.add((username, table_name, permission_type))
        elif issue_type == "EXCESSIVE_PERMISSION" and not expected_access and table_name and permission_type:
            excessive.add((username, table_name, permission_type))
    return dangling, missing, excessive


def _compare_findings(
    expected_dangling: set[str] | None,
    expected_missing: set[tuple[str, str, str]] | None,
    expected_excessive: set[tuple[str, str, str]] | None,
    dangling: set[str],
    missing: set[tuple[str, str, str]],
    excessive: set[tuple[str, str, str]],
) -> EvaluatorOutput:
    """Compare parsed findings to expected sets; return 1.0 or EvaluationReason."""
    if expected_dangling is not None and dangling != expected_dangling:
        return EvaluationReason(
            value=0.0,
            reason=f"Dangling users mismatch: got {dangling}, expected {expected_dangling}",
        )
    if expected_missing is not None and missing != expected_missing:
        return EvaluationReason(
            value=0.0,
            reason=f"Missing permissions: got {len(missing)}, expected {len(expected_missing)}",
        )
    if expected_excessive is not None and excessive != expected_excessive:
        return EvaluationReason(
            value=0.0,
            reason=f"Excessive permissions: got {len(excessive)}, expected {len(expected_excessive)}",
        )
    return 1.0
