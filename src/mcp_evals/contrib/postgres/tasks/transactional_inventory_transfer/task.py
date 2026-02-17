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

    def __init__(self, pg_config: PgConfig, tool_retries: int = 1) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.LEGO, tool_retries=tool_retries)
        self.evaluators = (
            TransactionalFunctionScenarioEvaluator(
                function_name="transfer_parts",
                audit_table="inventory_transfer_log",
                success_cases=SUCCESS_CASES,
                schema="public",
            ),
        )
