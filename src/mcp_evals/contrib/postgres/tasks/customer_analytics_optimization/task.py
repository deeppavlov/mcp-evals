"""Customer analytics query optimization in the dvdrental database (mcpmark parity: index verification)."""

from mcp_evals.contrib.postgres.common_evaluators import IndexExists
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig


class CustomerAnalyticsOptimizationTask(PostgresTask):
    """Task: optimize slow customer analytics query; verification checks index on payment.customer_id."""

    name = "customer_analytics_optimization"

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.DVD)
        self.evaluators = (IndexExists("payment", "customer_id"),)
