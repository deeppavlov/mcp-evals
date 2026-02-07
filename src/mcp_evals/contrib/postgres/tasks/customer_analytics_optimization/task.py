"""Customer analytics optimization in the dvdrental database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Create a table or view with customer analytics (e.g. rental count, spend, segment).
CUSTOMER_ANALYTICS_QUERY = """
SELECT * FROM customer_analytics ORDER BY customer_id
"""
# Ground truth: per-customer rental count and total payment amount
CUSTOMER_ANALYTICS_EXPECTED = """
SELECT
    p.customer_id,
    COUNT(DISTINCT p.rental_id)::BIGINT AS rental_count,
    COALESCE(SUM(p.amount), 0)::DECIMAL AS total_spend
FROM payment p
GROUP BY p.customer_id
ORDER BY p.customer_id
"""


class CustomerAnalyticsOptimizationTask(PostgresTask):
    """Task: create optimized customer analytics table or view in dvdrental."""

    name = "customer_analytics_optimization"
    goal = """Create an optimized customer analytics table or materialized view in the DVD rental database.

## Your Task

Create a table or view named **customer_analytics** that provides per-customer metrics for reporting:

- **customer_id** — customer identifier
- **rental_count** — number of paid rentals (count of distinct rental_id in payment)
- **total_spend** — sum of payment.amount for that customer

Use the **payment** table. Populate or define the object so it matches the ground truth (group by customer_id, aggregate from payment). Order by customer_id for verification.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.DVD)
        self.evaluators = (
            SqlResultMatches(
                CUSTOMER_ANALYTICS_QUERY,
                expected_query=CUSTOMER_ANALYTICS_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
        )
