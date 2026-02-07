"""Transactional inventory transfer function and audit in the lego database (mcpmark parity)."""

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import TransactionalFunctionScenarioEvaluator, TransferSuccessCase

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
    """Task: implement transfer_parts with inventory_transfer_log and validations (mcpmark parity)."""

    name = "transactional_inventory_transfer"
    goal = """Implement a transactional transfer of parts between inventories in the lego database with audit logging.

## Your Task

1. Create a function **transfer_parts(source_inventory_id, target_inventory_id, part_num, color_id, quantity, reason)**
   that:
   - Validates: source/target inventory and part/color exist, quantity between 1 and 500, sufficient quantity at source, no self-transfer (source ≠ target).
   - Decrements quantity in **lego_inventory_parts** for the source; increments (or inserts) for the target.
   - Logs each transfer in a table named **inventory_transfer_log** with at least: source_id, target_id, part_num, color_id, quantity, reason, transfer_status, error_message (or equivalent), timestamp.
   - Uses a single transaction (all or nothing). On validation failure, log the attempt with transfer_status/error_message and do not transfer.

2. The evaluator will call the function for a success case and verify source/target quantities and that a new row was written to **inventory_transfer_log**. Use schema **public** and **lego_inventory_parts** (inventory_id, part_num, color_id, quantity).
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.LEGO)
        self.evaluators = (
            TransactionalFunctionScenarioEvaluator(
                function_name="transfer_parts",
                audit_table="inventory_transfer_log",
                success_cases=SUCCESS_CASES,
                schema="public",
            ),
        )
