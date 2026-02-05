"""Evaluator that checks a database role exists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class RoleExists(Evaluator["PostgresTask", AgentRunResult]):
    """Check that the given role exists in pg_roles."""

    role_name: str

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Query pg_roles; return 1.0 if role exists."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (self.role_name,))
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Role '{self.role_name}' does not exist",
                )
        return 1.0
