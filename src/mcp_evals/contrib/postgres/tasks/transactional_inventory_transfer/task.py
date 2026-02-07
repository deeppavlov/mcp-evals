"""Transactional inventory transfer function and audit in the lego database."""

from mcp_evals.contrib.postgres.scenario_evaluators.transactional_inventory_transfer import (
    TransactionalFunctionScenarioEvaluator,
    TransferSuccessCase,
)
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Success case: transfer 5 units of part 3001 color 1 from inventory 1 to inventory 2.
# Adjust source_id/target_id/part_num/color_id if backup uses different data.
SUCCESS_CASES = [
    TransferSuccessCase(
        source_id=1,
        target_id=2,
        part_num="3001",
        color_id=1,
        quantity=5,
        reason="eval_verification",
    ),
]


class TransactionalInventoryTransferTask(PostgresTask):
    """Task: implement transfer function and audit log for lego inventory parts."""

    name = "transactional_inventory_transfer"
    goal = """Implement a transactional transfer of parts between inventories in the lego database with audit logging.

## Your Task

1. Create a function **transfer_parts(source_inventory_id, target_inventory_id, part_num, color_id, quantity, reason)**
   that:
   - Decrements quantity in lego_inventory_parts for the source inventory/part/color
   - Increments quantity for the target (or inserts a row if none)
   - Logs each transfer in an **audit table** (e.g. transfer_audit or inventory_transfer_log) with
     at least: source_id, target_id, part_num, color_id, quantity, reason, timestamp
   - Uses a single transaction (all or nothing)

2. The evaluator will call the function and verify source/target quantities and that a new audit row was written.
   Use schema **public** and table names **lego_inventory_parts** (inventory_id, part_num, color_id, quantity).
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.LEGO)
        self.evaluators = (
            TransactionalFunctionScenarioEvaluator(
                function_name="transfer_parts",
                audit_table="transfer_audit",
                success_cases=SUCCESS_CASES,
                schema="public",
            ),
        )
