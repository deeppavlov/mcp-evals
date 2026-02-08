"""Theme_analyst behavioral verification (mcpmark parity: 2 Star Wars sets, Technic.

blocked, reference/related tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import psycopg
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask

EXPECTED_STAR_WARS_SET_NUMS = frozenset({"65081-1", "K8008-1"})
EXPECTED_THEME_ID = 18  # theme_analyst -> Star Wars (mcpmark verify_theme_function)


class ThemeAnalystAccessEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify theme_analyst sees exactly 2 Star Wars sets, Technic blocked.

    reference/related tables accessible.
    """

    async def evaluate(  # noqa: PLR0911
        self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]
    ) -> EvaluatorOutput:
        """Run as theme_analyst and assert data access matches mcpmark test_theme_analyst_access."""
        task = ctx.inputs
        params = task.pg_conn_params()
        conn = await psycopg.AsyncConnection.connect(**params)
        try:
            async with conn.cursor() as cur:
                await cur.execute("SET ROLE theme_analyst")
                try:
                    # get_user_theme_id() returns EXPECTED_THEME_ID for theme_analyst
                    await cur.execute("SELECT get_user_theme_id()")
                    row = await cur.fetchone()
                    if row is None or row[0] != EXPECTED_THEME_ID:
                        got = row[0] if row is not None else None
                        return EvaluationReason(
                            value=0.0,
                            reason=f"get_user_theme_id() as theme_analyst expected "
                            f"{EXPECTED_THEME_ID}, got {got}",
                        )

                    # Star Wars sets: exactly 2 rows with set_num in {'65081-1', 'K8008-1'}
                    await cur.execute("SELECT set_num FROM lego_sets ORDER BY set_num")
                    set_rows = await cur.fetchall()
                    set_nums = {r[0] for r in set_rows}
                    if set_nums != EXPECTED_STAR_WARS_SET_NUMS:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"theme_analyst lego_sets expected set_nums "
                            f"{EXPECTED_STAR_WARS_SET_NUMS}, got {set_nums}",
                        )

                    # Technic (theme_id=1) blocked: 0 sets
                    await cur.execute("SELECT COUNT(*) FROM lego_sets WHERE theme_id = 1")
                    technic_count = (await cur.fetchone() or (0,))[0]
                    if technic_count != 0:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"theme_analyst should see 0 Technic sets, got {technic_count}",
                        )

                    # Reference table lego_themes accessible (> 10 rows)
                    await cur.execute("SELECT COUNT(*) > 10 FROM lego_themes")
                    ref_ok = (await cur.fetchone() or (False,))[0]
                    if not ref_ok:
                        return EvaluationReason(
                            value=0.0,
                            reason="theme_analyst lego_themes should be accessible with > 10 rows",
                        )

                    # Related tables: inventories and inventory_parts > 0
                    await cur.execute("SELECT COUNT(*) FROM lego_inventories")
                    inv_count = (await cur.fetchone() or (0,))[0]
                    if inv_count == 0:
                        return EvaluationReason(
                            value=0.0,
                            reason="theme_analyst should see at least one row in lego_inventories",
                        )
                    await cur.execute("SELECT COUNT(*) FROM lego_inventory_parts")
                    parts_count = (await cur.fetchone() or (0,))[0]
                    if parts_count == 0:
                        return EvaluationReason(
                            value=0.0,
                            reason="theme_analyst should see at least one row in lego_inventory_parts",
                        )
                finally:
                    await cur.execute("RESET ROLE")
        except (psycopg.Error, OSError) as e:
            await conn.rollback()
            return EvaluationReason(
                value=0.0,
                reason=f"theme_analyst access check failed: {e!s}",
            )
        else:
            return 1.0
        finally:
            await conn.close()
