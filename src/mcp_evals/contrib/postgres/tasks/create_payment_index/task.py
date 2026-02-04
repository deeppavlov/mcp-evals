"""Create an index on payment.customer_id in the dvdrental database."""

from mcp_evals.contrib.postgres.common_evaluators import IndexExists
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig


class CreatePaymentIndexTask(PostgresTask):
    """Task: create an index on the customer_id column of the payment table."""

    name = "create_payment_index"
    goal = """Create an index to optimize customer payment queries in the DVD rental database.

## Your Task

Create an index on the `customer_id` column of the `payment` table to improve query performance.

## Requirements

- Create an index on the `payment` table's `customer_id` column
- The index name can be anything you choose (e.g., `idx_payment_customer_id`)
- Use the standard CREATE INDEX syntax

## Why This Helps

The `customer_id` column is frequently used in:
- JOIN operations between customer and payment tables
- WHERE clauses filtering by customer
- Subqueries that look up payments for specific customers

Adding an index will significantly speed up these operations.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.DVD)
        self.evaluators = (IndexExists("payment", "customer_id"),)
