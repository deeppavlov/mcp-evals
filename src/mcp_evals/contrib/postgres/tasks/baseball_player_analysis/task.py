"""Baseball player analysis in the sports database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Table or view: player-level stats (schema depends on sports backup)
BASEBALL_PLAYER_QUERY = """
SELECT * FROM player_analysis ORDER BY player_id
"""
# Ground truth: aggregate from batting/players or equivalent; use common Lahman-style names
BASEBALL_PLAYER_EXPECTED = """
SELECT
    p.player_id,
    p.name,
    COALESCE(SUM(b.hits), 0)::BIGINT AS total_hits,
    COALESCE(SUM(b.home_runs), 0)::BIGINT AS total_hr
FROM players p
LEFT JOIN batting b ON b.player_id = p.player_id
GROUP BY p.player_id, p.name
ORDER BY p.player_id
"""


class BaseballPlayerAnalysisTask(PostgresTask):
    """Task: create baseball player analysis table or view in the sports database."""

    name = "baseball_player_analysis"
    goal = """Create a baseball player analysis table or view in the sports database.

## Your Task

Create a table or view (e.g. **player_analysis**) that provides per-player statistics, such as:

- **player_id** — player identifier
- **name** — player name
- **total_hits** — sum of hits from batting (or equivalent) table
- **total_hr** — sum of home runs

Use the existing **players** and **batting** (or similarly named) tables. If the schema uses different table/column names (e.g. Lahman-style), adapt accordingly. Order by player_id for verification.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.SPORTS)
        self.evaluators = (
            SqlResultMatches(
                BASEBALL_PLAYER_QUERY,
                expected_query=BASEBALL_PLAYER_EXPECTED,
            ),
        )
