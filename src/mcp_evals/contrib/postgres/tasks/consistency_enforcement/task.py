"""LEGO num_parts consistency: identify, fix, and enforce with deferrable constraint triggers (mcpmark parity)."""

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import LegoNumPartsConsistencyEvaluator


class ConsistencyEnforcementTask(PostgresTask):
    """Task: LEGO num_parts consistency (identify, fix, deferrable constraint triggers). mcpmark parity."""

    name = "consistency_enforcement"

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.LEGO)
        self.evaluators = (LegoNumPartsConsistencyEvaluator(),)
