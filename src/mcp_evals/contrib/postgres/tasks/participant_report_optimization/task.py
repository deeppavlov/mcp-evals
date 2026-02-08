"""Participant report optimization in the sports database."""

from mcp_evals.contrib.postgres.common_evaluators import IndexesExist, SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Actual: 5 data columns from the report table (agent deliverable)
PARTICIPANT_REPORT_QUERY = """
SELECT participant_id, event_count, stat_count, stat_type_count, last_event_date
FROM participant_performance_report
ORDER BY participant_id
"""
# Ground truth: exact query from original mcpmark (participants_events + stats + events)
PARTICIPANT_REPORT_EXPECTED = """
SELECT
    pe.participant_id,
    COUNT(pe.event_id) AS event_count,
    (SELECT COUNT(*) FROM stats s WHERE s.stat_holder_id = pe.participant_id AND \
     s.stat_holder_type = 'persons') AS stat_count,
    (SELECT COUNT(DISTINCT s.stat_repository_type) FROM stats s WHERE s.stat_holder_id = pe.participant_id AND \
     s.stat_holder_type = 'persons') AS stat_type_count,
    (SELECT MAX(e.start_date_time) FROM events e JOIN participants_events pe2 ON e.id = pe2.event_id \
     WHERE pe2.participant_id = pe.participant_id) AS last_event_date
FROM participants_events pe
WHERE pe.participant_id <= 50
GROUP BY pe.participant_id
ORDER BY pe.participant_id
"""


class ParticipantReportOptimizationTask(PostgresTask):
    """Task: create participant_performance_report table, optimize slow query, add indexes."""

    name = "participant_report_optimization"
    goal = """Create a performance report table and optimize a slow analytics query in the sports database.

## Your Task

### 1. Create the report table

Create a table named **participant_performance_report** with:

- **report_id** — serial primary key
- **participant_id** — integer NOT NULL, with CHECK (participant_id > 0)
- **event_count** — integer
- **stat_count** — integer
- **stat_type_count** — integer
- **last_event_date** — timestamp
- **created_at** — timestamp default current_timestamp

### 2. Optimize and populate

The following query is slow. Your task is to:

1. **Identify why the query is slow** (e.g. execution plan, missing indexes)
2. **Create appropriate indexes to optimize it**
3. **Populate participant_performance_report** with the query results

Slow query to optimize and use for populating the report:

```sql
SELECT
    pe.participant_id,
    COUNT(pe.event_id) AS event_count,
    (SELECT COUNT(*) FROM stats s WHERE s.stat_holder_id = pe.participant_id AND \
     s.stat_holder_type = 'persons') AS stat_count,
    (SELECT COUNT(DISTINCT s.stat_repository_type) FROM stats s WHERE s.stat_holder_id = pe.participant_id AND \
     s.stat_holder_type = 'persons') AS stat_type_count,
    (SELECT MAX(e.start_date_time) FROM events e JOIN participants_events pe2 ON e.id = pe2.event_id \
     WHERE pe2.participant_id = pe.participant_id) AS last_event_date
FROM participants_events pe
WHERE pe.participant_id <= 50
GROUP BY pe.participant_id
ORDER BY pe.participant_id;
```

Required optimizations (at least):

- Index on **participants_events(participant_id)**
- Index on **stats(stat_holder_type, stat_holder_id)** (or equivalent composite)

### 3. Success criteria

- The report table contains the correct rows matching the query above (participant_id <= 50).
- Both critical indexes exist so the query runs efficiently.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.SPORTS)
        self.evaluators = (
            SqlResultMatches(
                PARTICIPANT_REPORT_QUERY,
                expected_query=PARTICIPANT_REPORT_EXPECTED,
            ),
            IndexesExist(
                index_specs=[
                    ("participants_events", "participant_id"),
                    ("stats", ["stat_holder_type", "stat_holder_id"]),
                ],
            ),
        )
