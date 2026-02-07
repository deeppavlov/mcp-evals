"""Migrate MelodyMart customers into Customer table in the Chinook database."""

import importlib.resources
import json

from mcp_evals.contrib.postgres.common_evaluators import AggregateScalarMatches, QueryResultSetMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# All migrated rows (CustomerId > 59) must have SupportRepId = 3 and Fax IS NULL.
VIOLATION_COUNT_QUERY = """
SELECT COUNT(*)::INT FROM "Customer"
WHERE "CustomerId" > 59 AND ("SupportRepId" IS DISTINCT FROM 3 OR "Fax" IS NOT NULL)
"""
# Set comparison: migrated rows (CustomerId, SupportRepId, Fax) must equal (CustomerId, 3, NULL) for each id.
MIGRATED_QUERY = """
SELECT "CustomerId", "SupportRepId", "Fax" FROM "Customer" WHERE "CustomerId" > 59
"""
# Full row comparison: all 12 columns for migrated customers (mcpmark parity).
FULL_ROW_QUERY = """
SELECT "FirstName", "LastName", "Company", "Address", "City", "State",
       "Country", "PostalCode", "Phone", "Email", "SupportRepId", "Fax"
FROM "Customer" WHERE "CustomerId" > 59
"""

_COL_KEYS = (
    "FirstName",
    "LastName",
    "Company",
    "Address",
    "City",
    "State",
    "Country",
    "PostalCode",
    "Phone",
    "Email",
)


def _load_expected_migrated_rows() -> list[tuple[object, ...]]:
    """Load expected customer rows from customer_data.json (mcpmark canonical source)."""
    ref = importlib.resources.files("mcp_evals.contrib.postgres.tasks.customer_data_migration")
    text = (ref / "customer_data.json").read_text(encoding="utf-8")
    customers = json.load(text)
    result: list[tuple[object, ...]] = []
    for d in customers:
        row = tuple(str(d[k]) if d.get(k) is not None else "" for k in _COL_KEYS) + (3, None)
        result.append(row)
    return result


EXPECTED_MIGRATED_ROWS = _load_expected_migrated_rows()


class CustomerDataMigrationTask(PostgresTask):
    """Task: bulk migrate MelodyMart customers into Customer with SupportRepId=3 and Fax=NULL."""

    name = "customer_data_migration"
    goal = """Migrate MelodyMart customers into the Chinook **Customer** table as a bulk load.

## Your Task

1. Insert (or upsert) all MelodyMart source customers into the **Customer** table with:
   - **SupportRepId** = 3 for every migrated row
   - **Fax** = NULL for every migrated row
   - Migrated rows should have **CustomerId** > 59 (existing customers are 1–59)

2. Ensure every row with CustomerId > 59 has exactly SupportRepId = 3 and Fax IS NULL.
   The evaluator checks that no migrated row violates these two conditions and that the set of (CustomerId, SupportRepId, Fax) for CustomerId > 59 matches the expected (id, 3, NULL).
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.CHI)
        # Expected: one row per migrated id with (CustomerId, 3, NULL)
        expected_set_query = """
SELECT "CustomerId", 3::INTEGER, NULL::character varying
FROM (SELECT "CustomerId" FROM "Customer" WHERE "CustomerId" > 59) sub
"""
        self.evaluators = (
            AggregateScalarMatches(
                query=VIOLATION_COUNT_QUERY,
                expected=0,
            ),
            QueryResultSetMatches(
                query=MIGRATED_QUERY,
                expected_query=expected_set_query,
            ),
            QueryResultSetMatches(
                query=FULL_ROW_QUERY,
                expected_rows=EXPECTED_MIGRATED_ROWS,
            ),
        )
