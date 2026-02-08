"""Participant report optimization in the sports database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Table or view: participant/event report
PARTICIPANT_REPORT_QUERY = """
SELECT * FROM participant_report ORDER BY participant_id
"""
# Ground truth: participants with event count or similar
PARTICIPANT_REPORT_EXPECTED = """
SELECT
    p.participant_id,
    p.name,
    COUNT(e.event_id)::BIGINT AS event_count
FROM participants p
LEFT JOIN events e ON e.participant_id = p.participant_id
GROUP BY p.participant_id, p.name
ORDER BY p.participant_id
"""


class ParticipantReportOptimizationTask(PostgresTask):
    """Task: create optimized participant report table or view in the sports database."""

    name = "participant_report_optimization"
    goal = """Create an optimized participant report table or view in the sports database.

## Your Task

Create a table or view (e.g. **participant_report**) that summarizes participants and their events:

- **participant_id** — participant identifier
- **name** — participant name
- **event_count** — number of events (or equivalent) for that participant

Use the existing **participants** and **events** (or similarly named) tables. Adapt table/column names to match the \
backup schema. Order by participant_id for verification.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.SPORTS)
        self.evaluators = (
            SqlResultMatches(
                PARTICIPANT_REPORT_QUERY,
                expected_query=PARTICIPANT_REPORT_EXPECTED,
            ),
        )
