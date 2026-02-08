"""Evaluator that checks a function or procedure exists."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask


@dataclass
class FunctionExists(Evaluator["PostgresTask", AgentRunResult]):
    """Check that a function or procedure exists in the schema."""

    routine_name: str
    schema: str = "public"
    routine_type: str = "FUNCTION"

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Query information_schema.routines; return 1.0 if routine exists."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1 FROM information_schema.routines
                WHERE routine_schema = %s AND routine_name = %s AND routine_type = %s
                """,
                (self.schema, self.routine_name, self.routine_type),
            )
            if await cur.fetchone() is None:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Routine {self.schema}.{self.routine_name} ({self.routine_type}) does not exist",
                )
        return 1.0
