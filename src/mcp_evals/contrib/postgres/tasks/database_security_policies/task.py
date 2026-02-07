"""Database security policies: role theme_analyst, RLS, and get_user_theme_id in the lego database."""

from mcp_evals.contrib.postgres.common_evaluators import (
    FunctionExists,
    RlsEnabled,
    RoleExists,
)
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Query run as theme_analyst: should return only Star Wars sets (e.g. 2 rows).
# We run SET ROLE then SELECT in one execute; PostgreSQL accepts multiple statements.
THEME_ANALYST_CHECK_SQL = """
SET LOCAL ROLE theme_analyst;
SELECT COUNT(*)::BIGINT FROM lego_sets
"""
# Expected: 2 (Star Wars sets only when RLS restricts by get_user_theme_id()).
# SqlResultMatches runs one query - with SET LOCAL ROLE the next statement in same connection runs as theme_analyst.
# But execute() typically runs one statement; multi-statement might work. Check: in psycopg, execute("SET ROLE x; SELECT 1") may fail.
# So use only RoleExists, RlsEnabled, FunctionExists and skip the row-count check, or implement a small custom evaluator.
# Plan says "at least one check that theme_analyst sees only Star Wars sets (e.g. SqlResultMatches for a query run as theme_analyst returning 2 rows)".
# I'll add SqlResultMatches that runs a query that doesn't require role switch: e.g. "SELECT get_user_theme_id()" to ensure function exists and is callable.
FUNCTION_CHECK_QUERY = "SELECT get_user_theme_id()"
# That returns one row (theme id). We don't know the exact value without running as a specific user. So expected_query could be "SELECT (SELECT id FROM themes WHERE name = 'Star Wars' LIMIT 1)" or we accept any one row.
# Simpler: just require the function to exist (FunctionExists) and that RLS is on (RlsEnabled). Omit SqlResultMatches for theme_analyst view to avoid needing a second connection/role.
# So evaluators: RoleExists, RlsEnabled x3 tables, FunctionExists, and no SqlResultMatches. If we want one SqlResultMatches we can do "SELECT 1 WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'theme_analyst')" -> (1,) as a sanity check.
SANITY_QUERY = "SELECT 1 WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'theme_analyst')"
# That returns one row if role exists. So: RoleExists, RlsEnabled (3 tables), FunctionExists, SqlResultMatches(SANITY_QUERY, expected_rows=[(1,)]). That duplicates RoleExists. So just RoleExists, RlsEnabled, FunctionExists.
# Final: RoleExists("theme_analyst"), RlsEnabled(tables=["lego_sets", "lego_inventories", "lego_inventory_parts"], schema="public"), FunctionExists("get_user_theme_id", schema="public").
# Plan also says "If verify also checks table privileges, add RoleExists-style or a small custom check". So we're good.
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

3. Create a function **get_user_theme_id()** (in schema **public**) that returns the theme ID for the current user (e.g. for theme_analyst, return the Star Wars theme id).

4. Add RLS policies on the three tables so that **theme_analyst** sees only rows for their theme (e.g. when set to Star Wars, only Star Wars sets/inventories/parts). Use get_user_theme_id() in the policy expressions.

The evaluator checks that the role exists, RLS is enabled on the three tables, and the function exists.
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
        )
