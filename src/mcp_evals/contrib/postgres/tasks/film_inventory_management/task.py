"""Film inventory management in the dvdrental database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Table or view for film inventory (e.g. film_id, title, stock count per store)
FILM_INVENTORY_QUERY = """
SELECT * FROM film_inventory_summary ORDER BY film_id, store_id
"""
# Ground truth: film + store inventory count from inventory
FILM_INVENTORY_EXPECTED = """
SELECT
    i.film_id,
    f.title,
    i.store_id,
    COUNT(*)::BIGINT AS in_stock
FROM inventory i
JOIN film f ON f.film_id = i.film_id
GROUP BY i.film_id, f.title, i.store_id
ORDER BY i.film_id, i.store_id
"""


class FilmInventoryManagementTask(PostgresTask):
    """Task: create film inventory summary table or view in dvdrental."""

    name = "film_inventory_management"
    goal = """Create a film inventory management table or view in the DVD rental database.

## Your Task

Create a table or view named **film_inventory_summary** that summarizes inventory by film and store:

- **film_id** — film identifier
- **title** — film title (from film table)
- **store_id** — store identifier
- **in_stock** — count of inventory rows for that film and store

Use the **inventory** and **film** tables. Populate or define the object so it matches the ground truth (join inventory and film, group by film_id, title, store_id). Order by film_id, store_id for verification.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.DVD)
        self.evaluators = (
            SqlResultMatches(
                FILM_INVENTORY_QUERY,
                expected_query=FILM_INVENTORY_EXPECTED,
            ),
        )
