"""Evaluator that checks a scalar aggregate (e.g. COUNT) matches expected value(s)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask

FLOAT_TOLERANCE = 0.1


def _scalar_match(
    actual: object,
    expected: object,
) -> bool:
    """Compare scalar with tolerance for numeric types."""
    if actual == expected:
        return True
    if isinstance(actual, Decimal) and isinstance(expected, (Decimal, float, int)):
        return abs(float(actual) - float(expected)) <= FLOAT_TOLERANCE
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) <= FLOAT_TOLERANCE
    return False


@dataclass
class AggregateScalarMatches(Evaluator["PostgresTask", AgentRunResult]):
    """Run a query that returns a single row of scalar values and compare to expected.

    query: SQL returning one row (e.g. SELECT COUNT(*), COUNT(*) FILTER (WHERE ...) FROM t).
    expected: One value or tuple of values in same order as query columns.
    """

    query: str
    expected: Any

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Execute query; compare single-row result to expected."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(self.query)
            row = await cur.fetchone()
        if row is None:
            return EvaluationReason(value=0.0, reason="Query returned no rows")
        actual = row[0] if len(row) == 1 else tuple(row)
        exp = self.expected
        if isinstance(exp, tuple) and len(exp) != len(row):
            return EvaluationReason(
                value=0.0,
                reason=f"Column count mismatch: got {len(row)}, expected {len(exp)}",
            )
        if isinstance(exp, tuple):
            for i, (a, e) in enumerate(zip(actual, exp, strict=True)):
                if not _scalar_match(a, e):
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Position {i} mismatch: got {a}, expected {e}",
                    )
        elif not _scalar_match(actual, exp):
            return EvaluationReason(
                value=0.0,
                reason=f"Scalar mismatch: got {actual}, expected {exp}",
            )
        return 1.0
