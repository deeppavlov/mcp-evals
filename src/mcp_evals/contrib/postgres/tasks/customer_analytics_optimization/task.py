"""Customer analytics query optimization in the dvdrental database (mcpmark parity: index verification)."""

from mcp_evals.contrib.postgres.common_evaluators import IndexExists
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig


class CustomerAnalyticsOptimizationTask(PostgresTask):
    """Task: optimize slow customer analytics query; verification checks index on payment.customer_id."""

    name = "customer_analytics_optimization"
    goal = """Optimize a slow customer analytics query in the DVD rental database.

## Your Task

A customer analytics query (e.g. aggregating payments or rentals by customer, joining payment with customer) is running slowly. You must:

1. Identify the query (e.g. via application code, common reporting queries, or EXPLAIN ANALYZE).
2. Improve performance by adding an appropriate **index** (e.g. on **payment.customer_id**, which is frequently used in JOINs and WHERE clauses for customer-level analytics).
3. Optionally use EXPLAIN ANALYZE before and after to confirm improvement.

The evaluator verifies only that an **index exists on the payment table that references the customer_id column** (no result-correctness check). Use the standard `payment` and `customer` tables in the public schema.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.DVD)
        self.evaluators = (IndexExists("payment", "customer_id"),)
