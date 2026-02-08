"""Database security policies: role theme_analyst, RLS, and get_user_theme_id in the lego database."""

from mcp_evals.contrib.postgres.common_evaluators import FunctionExists, RlsEnabled, RoleExists
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import ThemeAnalystAccessEvaluator


class DatabaseSecurityPoliciesTask(PostgresTask):
    """Task: create role theme_analyst, RLS on lego tables, and get_user_theme_id function."""

    name = "database_security_policies"

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.LEGO)
        self.evaluators = (
            RoleExists("theme_analyst"),
            RlsEnabled(
                tables=["lego_sets", "lego_inventories", "lego_inventory_parts"],
                schema="public",
            ),
            FunctionExists("get_user_theme_id", schema="public"),
            ThemeAnalystAccessEvaluator(),
        )
