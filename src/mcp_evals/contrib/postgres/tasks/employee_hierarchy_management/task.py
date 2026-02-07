"""Employee hierarchy and customer assignment management in the Chinook database."""

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import HierarchyAndAssignmentScenarioEvaluator

# Chinook: quoted identifiers, schema public.
# required_tables: Employee, Customer, and optional employee_performance (agent may create)
REQUIRED_TABLES = ["Employee", "Customer"]
REQUIRED_COLUMNS = [
    ("Employee", ["EmployeeId", "LastName", "FirstName", "Title", "ReportsTo"]),
    ("Customer", ["CustomerId", "SupportRepId"]),
]
# Scalar checks: e.g. total employees 9, customers with SupportRepId=1 -> 1, etc.
# Plan: scalar_checks (final count query → (9, 1, 0, 4))
SCALAR_CHECKS = [
    ('SELECT COUNT(*)::INT FROM "Employee"', 9),
    ('SELECT COUNT(*)::INT FROM "Customer" WHERE "SupportRepId" = 1', 1),
    ('SELECT COUNT(*)::INT FROM "Customer" WHERE "SupportRepId" = 2', 0),
    ('SELECT COUNT(*)::INT FROM "Customer" WHERE "SupportRepId" = 3', 4),
]
# Row checks: employees 1, 2, 9, 10 - at least Title and key columns
ROW_CHECKS = [
    (
        'SELECT "EmployeeId", "Title", "ReportsTo" FROM "Employee" WHERE "EmployeeId" = 1',
        (1, "General Manager", None),
    ),
    (
        'SELECT "EmployeeId", "Title", "ReportsTo" FROM "Employee" WHERE "EmployeeId" = 2',
        (2, "Sales Manager", 1),
    ),
]


class EmployeeHierarchyManagementTask(PostgresTask):
    """Task: manage employee hierarchy and customer assignments (insert/update/delete, employee_performance, salary column)."""

    name = "employee_hierarchy_management"
    goal = """Manage employee hierarchy and customer assignments in the Chinook database.

## Your Task

1. Ensure the **Employee** table has the expected structure (EmployeeId, LastName, FirstName, Title, ReportsTo, etc.)
   and that **Customer** has SupportRepId linking to Employee.

2. Maintain these invariants (the evaluator will check):
   - Total employee count: 9
   - Exactly 1 customer with SupportRepId = 1
   - 0 customers with SupportRepId = 2
   - 4 customers with SupportRepId = 3
   - Employee 1: Title 'General Manager', ReportsTo NULL
   - Employee 2: Title 'Sales Manager', ReportsTo 1

3. Optionally add an **employee_performance** table or a **salary** column on Employee if the task description requires it; otherwise the evaluator checks only Employee and Customer counts and sample rows above.

Use quoted identifiers: "Employee", "Customer", "EmployeeId", "SupportRepId", "Title", "ReportsTo".
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.CHI)
        self.evaluators = (
            HierarchyAndAssignmentScenarioEvaluator(
                required_tables=REQUIRED_TABLES,
                schema="public",
                required_columns=REQUIRED_COLUMNS,
                scalar_checks=SCALAR_CHECKS,
                row_checks=ROW_CHECKS,
            ),
        )
