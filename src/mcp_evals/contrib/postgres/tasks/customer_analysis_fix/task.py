"""Fix buggy customer analysis query and create customer_analysis_fixed table in dvdrental."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Query the created table (agent builds customer_analysis_fixed with correct logic)
CUSTOMER_ANALYSIS_QUERY = """
SELECT customer_id, paid_rentals, total_spending
FROM customer_analysis_fixed
ORDER BY customer_id
"""
# Ground truth: paid rentals count and sum of payment.amount per customer
CUSTOMER_ANALYSIS_EXPECTED = """
SELECT
    p.customer_id,
    COUNT(DISTINCT p.rental_id)::BIGINT AS paid_rentals,
    COALESCE(SUM(p.amount), 0)::DECIMAL AS total_spending
FROM payment p
GROUP BY p.customer_id
ORDER BY customer_id
"""


class CustomerAnalysisFixTask(PostgresTask):
    """Task: fix buggy customer analysis and create customer_analysis_fixed with correct results."""

    name = "customer_analysis_fix"
    goal = """Fix the buggy customer analysis and create a correct results table in the DVD rental database.

## Your Task

A customer analysis query has bugs (e.g. wrong joins or aggregates). You must:

1. Identify and fix the logic so that for each customer we correctly compute:
   - **paid_rentals** — count of distinct rentals that have a payment (from payment.rental_id)
   - **total_spending** — sum of payment.amount for that customer

2. Create a table named **customer_analysis_fixed** with columns:
   - customer_id (integer)
   - paid_rentals (bigint or integer)
   - total_spending (numeric/decimal)

3. Populate it with the correct results (one row per customer, ordered by customer_id for verification).

Use the `payment` and optionally `rental` tables. Ensure decimal precision is preserved for total_spending (e.g. numeric/decimal type).
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.DVD)
        self.evaluators = (
            SqlResultMatches(
                CUSTOMER_ANALYSIS_QUERY,
                expected_query=CUSTOMER_ANALYSIS_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
        )
