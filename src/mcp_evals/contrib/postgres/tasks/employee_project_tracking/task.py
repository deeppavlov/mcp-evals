"""Project and employee relationship tables in the employees database."""

from mcp_evals.contrib.postgres.scenario_evaluators import ProjectTrackingRelationshipScenarioEvaluator
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Required: projects and project_assignments (or similar) in employees schema
# with columns and indexes for employee–project relationships.
REQUIRED_TABLES = ["projects", "project_assignments"]
TABLE_COLUMNS = [
    ("projects", ["project_id", "name"]),
    ("project_assignments", ["employee_id", "project_id"]),
]
INDEX_SPECS = [
    ("project_assignments", "employee_id"),
    ("project_assignments", "project_id"),
]
# Optional: relationship checks (query, expected_count)
RELATIONSHIP_QUERIES = [
    ("SELECT COUNT(*) FROM employees.project_assignments", 0),  # placeholder; adjust if backup pre-populates
]


class EmployeeProjectTrackingTask(PostgresTask):
    """Task: create project and employee-project relationship tables with constraints and indexes."""

    name = "employee_project_tracking"
    goal = """Create project tracking tables in the employees database to link employees to projects.

## Your Task

1. Create table **employees.projects** with at least:
   - project_id (primary key)
   - name (or title)

2. Create table **employees.project_assignments** with at least:
   - employee_id (references employees.employee.id or equivalent)
   - project_id (references employees.projects.project_id)
   - Unique or primary key on (employee_id, project_id) if one employee can be on a project once

3. Add indexes to support lookups:
   - Index on project_assignments(employee_id)
   - Index on project_assignments(project_id)

4. Populate if the task requires sample data; otherwise leave empty. The evaluator checks table and column existence and optional relationship counts.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL)
        self.evaluators = (
            ProjectTrackingRelationshipScenarioEvaluator(
                required_tables=REQUIRED_TABLES,
                table_columns=TABLE_COLUMNS,
                index_specs=INDEX_SPECS,
                schema="employees",
                relationship_queries=RELATIONSHIP_QUERIES,
            ),
        )
