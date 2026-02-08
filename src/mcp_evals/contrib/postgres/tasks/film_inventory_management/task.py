"""Film inventory management in the dvdrental database (mcpmark parity: per-film summary + workflow)."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Per-film summary (one row per film): title, rental_rate, total_inventory, store1_count, store2_count
FILM_INVENTORY_QUERY = """
SELECT title, rental_rate, total_inventory, store1_count, store2_count
FROM film_inventory_summary
ORDER BY total_inventory DESC, title ASC
"""
# Ground truth: from current film + inventory state (after workflow)
FILM_INVENTORY_EXPECTED = """
SELECT
    f.title,
    f.rental_rate,
    COUNT(i.inventory_id)::BIGINT AS total_inventory,
    COUNT(*) FILTER (WHERE i.store_id = 1)::BIGINT AS store1_count,
    COUNT(*) FILTER (WHERE i.store_id = 2)::BIGINT AS store2_count
FROM film f
LEFT JOIN inventory i ON i.film_id = f.film_id
GROUP BY f.film_id, f.title, f.rental_rate
ORDER BY total_inventory DESC, f.title ASC
"""


class FilmInventoryManagementTask(PostgresTask):
    """Task: six-step film inventory workflow and per-film summary table (mcpmark parity)."""

    name = "film_inventory_management"

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.DVD)
        self.evaluators = (
            SqlResultMatches(
                FILM_INVENTORY_QUERY,
                expected_query=FILM_INVENTORY_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
        )
