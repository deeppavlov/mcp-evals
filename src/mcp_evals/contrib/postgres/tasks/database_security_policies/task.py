"""Database security policies: role theme_analyst, RLS, and get_user_theme_id in the lego database."""

from mcp_evals.contrib.postgres.common_evaluators import FunctionExists, RlsEnabled, RoleExists
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import ThemeAnalystAccessEvaluator


class DatabaseSecurityPoliciesTask(PostgresTask):
    """Task: create role theme_analyst, RLS on lego tables, and get_user_theme_id function."""

    name = "database_security_policies"
    goal = """Implement database security policies in the lego database for theme-based access.

## Your Task

1. Create a role **theme_analyst** (e.g. CREATE ROLE theme_analyst LOGIN).

2. Enable **Row-Level Security (RLS)** on:
   - **lego_sets**
   - **lego_inventories**
   - **lego_inventory_parts**
   (schema **public**.)

3. Create a function **get_user_theme_id()** (in schema **public**) that returns the theme ID for the current user \
(e.g. for theme_analyst, return the Star Wars theme id).

4. Add RLS policies on the three tables so that **theme_analyst** sees only rows for their theme (e.g. when set to \
Star Wars, only Star Wars sets/inventories/parts). Use get_user_theme_id() in the policy expressions.

The evaluators check that the role exists, RLS is enabled on the three tables, the function exists, and that \
theme_analyst sees exactly 2 Star Wars sets (behavioral verification).
"""

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
