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
    goal = """Complete the film inventory management workflow in the DVD rental database and create a per-film summary.

## Your Task

1. **Add 2 new films** to the **film** table (title, rental_rate, length, etc. as appropriate).

2. **Add inventory** for the new films: 3 copies in store 1 and 2 copies in store 2 for each new film (in **inventory**).

3. **Update** all films with rating **PG-13**: set **rental_rate** to 10% more than current (e.g. rental_rate * 1.10).

4. Create a view or table **available_films** that lists films **available in store 1** with **rental_rate between 3 and 5** and **length > 100** (from **film** and **inventory**).

5. **Cleanup inventory**: remove inventory rows where the film has **replacement_cost > 25** and **rental_rate < 1**, and the inventory item has **no rentals** (no row in **rental**). Leave all other inventory unchanged.

6. Create a table or view **film_inventory_summary** with **one row per film** and columns:
   - **title** — film title
   - **rental_rate** — film rental rate
   - **total_inventory** — total count of inventory rows for that film (all stores)
   - **store1_count** — count of inventory rows for that film in store_id = 1
   - **store2_count** — count of inventory rows for that film in store_id = 2

Use **film** and **inventory** (and **rental** for cleanup). Order **film_inventory_summary** by total_inventory \
from highest to lowest, then alphabetically by film title; verification uses that order. The evaluator compares \
your summary to a ground-truth query over the current film and inventory state (with decimal tolerance).
"""

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
