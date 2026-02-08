"""Team roster management in the sports database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Table or view: team roster (team + players)
TEAM_ROSTER_QUERY = """
SELECT * FROM team_roster ORDER BY team_id, player_id
"""
# Ground truth: roster join (teams + roster/players)
TEAM_ROSTER_EXPECTED = """
SELECT
    t.team_id,
    t.team_name,
    r.player_id,
    p.name AS player_name
FROM teams t
JOIN roster r ON r.team_id = t.team_id
JOIN players p ON p.player_id = r.player_id
ORDER BY t.team_id, r.player_id
"""


class TeamRosterManagementTask(PostgresTask):
    """Task: create team roster table or view in the sports database."""

    name = "team_roster_management"
    goal = """Create a team roster management table or view in the sports database.

## Your Task

Create a table or view (e.g. **team_roster**) that lists team-player associations:

- **team_id** — team identifier
- **team_name** — team name
- **player_id** — player identifier
- **player_name** — player name

Use the existing **teams**, **roster** (or equivalent), and **players** tables. Adapt table/column names to match the \
backup schema. Order by team_id, player_id for verification.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.SPORTS)
        self.evaluators = (
            SqlResultMatches(
                TEAM_ROSTER_QUERY,
                expected_query=TEAM_ROSTER_EXPECTED,
            ),
        )
