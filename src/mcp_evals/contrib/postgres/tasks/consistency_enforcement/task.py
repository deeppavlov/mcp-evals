"""Deferred constraint scenario in the lego database.

Note: mcpmark's consistency_enforcement task was about LEGO num_parts consistency (stored num_parts
vs sum of non-spare parts in latest inventory) with deferrable constraint *triggers* on
lego_sets, lego_inventories, lego_inventory_parts. This mcp_evals task is a *different* scenario:
deferrable *foreign key* (e.g. lego_sets.theme_id → themes), so that an update to an invalid
theme_id fails immediately, but with SET CONSTRAINTS ALL DEFERRED an insert of the theme plus
update succeeds. Both test deferrable constraints; the business rule and verification differ.
"""

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import DeferredConstraintScenarioEvaluator

# Scenario: an update that would violate FK if checked immediately; with DEFERRED it succeeds.
# Assumes lego schema has themes (id, name) and lego_sets (set_num, theme_id) with deferrable FK.
# Failing: set theme_id to a non-existent theme (999999).
# Deferred: insert theme 999999 then update one lego_set (valid at commit).
FAILING_SQL = """
UPDATE lego_sets SET theme_id = 999999
WHERE set_num = (SELECT set_num FROM lego_sets WHERE theme_id IS NOT NULL LIMIT 1)
"""
DEFERRED_SQL_BLOCKS = [
    "INSERT INTO themes (id, name) VALUES (999999, 'eval_placeholder') ON CONFLICT (id) DO NOTHING",
    "UPDATE lego_sets SET theme_id = 999999 WHERE set_num = (SELECT set_num FROM lego_sets WHERE theme_id IS NOT NULL LIMIT 1)",
]


class ConsistencyEnforcementTask(PostgresTask):
    """Task: implement deferrable FK (theme_id) so invalid op fails and deferred block succeeds.

    This is intentionally a deferrable-FK scenario, not mcpmark's num_parts trigger scenario.
    """

    name = "consistency_enforcement"
    goal = """Implement deferrable constraints in the lego database so that operations that temporarily
violate a constraint can succeed when the constraint is deferred.

## Your Task

1. Ensure the database has at least one **DEFERRABLE** constraint (e.g. a foreign key from lego_sets to themes)
   that is checked at commit when deferred, and at statement end when immediate.

2. The evaluator will:
   - Run an update that violates the constraint (e.g. set theme_id to a non-existent theme) and expect it to **fail**.
   - In a new transaction with **SET CONSTRAINTS ALL DEFERRED**, run: (a) insert the missing theme (id 999999),
     (b) update one lego_set row to theme_id 999999. This must **succeed** (constraint checked at commit).

Use the existing tables (e.g. themes, lego_sets). If the FK is not already deferrable, alter or recreate it as
DEFERRABLE INITIALLY IMMEDIATE. Constraint names are optional; the evaluator uses SET CONSTRAINTS ALL DEFERRED.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.LEGO)
        self.evaluators = (
            DeferredConstraintScenarioEvaluator(
                failing_sql=FAILING_SQL,
                deferred_sql_blocks=DEFERRED_SQL_BLOCKS,
            ),
        )
