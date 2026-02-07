"""LEGO num_parts consistency verification (mcpmark parity: mismatch count, constraint triggers, violation blocked, deferred update allowed)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask

TABLES_WITH_CONSTRAINT_TRIGGERS = [
    "public.lego_inventory_parts",
    "public.lego_inventories",
    "public.lego_sets",
]

MISMATCH_COUNT_QUERY = """
WITH latest_inv AS (
    SELECT set_num, MAX(version) AS max_version
    FROM public.lego_inventories
    GROUP BY set_num
), inv_latest AS (
    SELECT li.set_num, li.id
    FROM public.lego_inventories li
    JOIN latest_inv lv ON lv.set_num = li.set_num AND lv.max_version = li.version
), parts_agg AS (
    SELECT
        i.set_num,
        SUM(lip.quantity) AS actual_parts
    FROM inv_latest i
    JOIN public.lego_inventory_parts lip ON lip.inventory_id = i.id
    WHERE lip.is_spare = false
    GROUP BY i.set_num
)
SELECT COUNT(*)
FROM public.lego_sets s
LEFT JOIN parts_agg pa ON s.set_num = pa.set_num
WHERE s.num_parts <> COALESCE(pa.actual_parts, 0);
"""

CANDIDATE_PART_ROW_QUERY = """
WITH latest_inv AS (
    SELECT set_num, MAX(version) AS max_version
    FROM public.lego_inventories
    GROUP BY set_num
), inv AS (
    SELECT li.id, li.set_num
    FROM public.lego_inventories li
    JOIN latest_inv lv ON lv.set_num = li.set_num AND lv.max_version = li.version
)
SELECT i.id AS inventory_id, i.set_num, lip.part_num, lip.color_id
FROM inv i
JOIN public.lego_inventory_parts lip ON lip.inventory_id = i.id
WHERE lip.is_spare = false AND lip.quantity > 0
LIMIT 1;
"""


class LegoNumPartsConsistencyEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """mcpmark parity: mismatch count in {0,1}, constraint triggers on three tables, violation blocked, deferred allowed."""

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Run four checks: data consistency, triggers exist, violation blocked, deferred update then revert."""
        task = ctx.inputs
        params = task.pg_conn_params()
        fail = None

        # Step 1: Data consistency (mismatch count 0 or 1)
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(MISMATCH_COUNT_QUERY)
            row = await cur.fetchone()
        count = row[0] if row else 0
        if count > 1:
            fail = EvaluationReason(
                value=0.0,
                reason=f"Expected 0 or 1 sets with inconsistent part counts, got {count}",
            )

        # Step 2: Constraint triggers exist on all three tables
        if fail is None:
            async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
                for table in TABLES_WITH_CONSTRAINT_TRIGGERS:
                    await cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM pg_trigger
                        WHERE tgrelid = %s::regclass AND tgconstraint <> 0
                        """,
                        (table,),
                    )
                    trigger_count = (await cur.fetchone() or (0,))[0]
                    if trigger_count == 0:
                        fail = EvaluationReason(
                            value=0.0,
                            reason=f"No constraint trigger found on table {table!r}",
                        )
                        break

        # Step 3: Inconsistent write must be blocked
        if fail is None:
            async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
                await cur.execute(CANDIDATE_PART_ROW_QUERY)
                candidate = await cur.fetchone()
            if candidate is not None:
                inventory_id, set_num, part_num, color_id = (
                    candidate[0],
                    candidate[1],
                    candidate[2],
                    candidate[3],
                )
                async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
                    try:
                        await cur.execute(
                            """
                            UPDATE public.lego_inventory_parts
                            SET quantity = quantity + 1
                            WHERE inventory_id = %s AND part_num = %s AND color_id = %s
                            """,
                            (inventory_id, part_num, color_id),
                        )
                        await conn.rollback()
                        fail = EvaluationReason(
                            value=0.0,
                            reason="Inconsistent write was not blocked by the trigger",
                        )
                    except psycopg.Error:
                        await conn.rollback()

        # Step 4: Deferred coordinated update must succeed, then revert
        if fail is not None:
            return fail
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await cur.execute(CANDIDATE_PART_ROW_QUERY)
            candidate = await cur.fetchone()
        if candidate is None:
            return 1.0  # skip deferred test (pass)
        inventory_id, set_num, part_num, color_id = (
            candidate[0],
            candidate[1],
            candidate[2],
            candidate[3],
        )

        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await conn.set_autocommit(False)
            try:
                await cur.execute("SET CONSTRAINTS ALL DEFERRED")
                await cur.execute(
                    """
                    UPDATE public.lego_inventory_parts SET quantity = quantity + 1
                    WHERE inventory_id = %s AND part_num = %s AND color_id = %s
                    """,
                    (inventory_id, part_num, color_id),
                )
                await cur.execute(
                    "UPDATE public.lego_sets SET num_parts = num_parts + 1 WHERE set_num = %s",
                    (set_num,),
                )
                await conn.commit()
            except psycopg.Error as e:
                await conn.rollback()
                return EvaluationReason(
                    value=0.0,
                    reason=f"Deferred transaction failed to commit: {e!s}",
                )

        # Revert to leave DB in original state
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            await conn.set_autocommit(False)
            try:
                await cur.execute("SET CONSTRAINTS ALL DEFERRED")
                await cur.execute(
                    """
                    UPDATE public.lego_inventory_parts SET quantity = quantity - 1
                    WHERE inventory_id = %s AND part_num = %s AND color_id = %s
                    """,
                    (inventory_id, part_num, color_id),
                )
                await cur.execute(
                    "UPDATE public.lego_sets SET num_parts = num_parts - 1 WHERE set_num = %s",
                    (set_num,),
                )
                await conn.commit()
            except psycopg.Error as e:
                await conn.rollback()
                return EvaluationReason(
                    value=0.0,
                    reason=f"Revert after deferred update failed: {e!s}",
                )

        return 1.0
