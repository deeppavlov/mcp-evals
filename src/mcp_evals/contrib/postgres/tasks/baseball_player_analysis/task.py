"""Baseball player analysis in the sports database."""

from decimal import Decimal
from typing import Any

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Query that reads the solution table (same columns and order as canonical)
BASEBALL_PLAYER_QUERY = """
SELECT player_id, player_name, team_name, games_played, at_bats, hits,
       runs_scored, rbi, home_runs, batting_average, defensive_games,
       putouts, assists, errors, fielding_percentage
FROM baseball_player_analysis
ORDER BY batting_average DESC, games_played DESC
"""

# Canonical expected result (sportsdb: persons, display_names, stats,
# baseball_offensive_stats, core_person_stats, baseball_defensive_stats)
BASEBALL_PLAYER_EXPECTED = """
SELECT
p.id AS player_id,
MAX(dn.full_name) AS player_name,
'Unknown' AS team_name,
core.events_played AS games_played,
off.at_bats,
off.hits,
off.runs_scored,
off.rbi,
off.home_runs,
CASE WHEN off.at_bats > 0
    THEN 1.0 * off.hits / off.at_bats
    ELSE 0
END AS batting_average,
core.events_played AS defensive_games,
COALESCE(def.putouts, 0)  AS putouts,
COALESCE(def.assists, 0)  AS assists,
COALESCE(def.errors, 0)   AS errors,
CASE
    WHEN (COALESCE(def.putouts,0) + COALESCE(def.assists,0) + COALESCE(def.errors,0)) > 0
    THEN 1.0 * (COALESCE(def.putouts,0) + COALESCE(def.assists,0))
        / (COALESCE(def.putouts,0) + COALESCE(def.assists,0) + COALESCE(def.errors,0))
    ELSE 0
END AS fielding_percentage
FROM persons p
JOIN display_names dn
ON dn.entity_id = p.id
AND dn.entity_type = 'persons'
AND NULLIF(TRIM(dn.full_name), '') IS NOT NULL
JOIN (
SELECT s.stat_holder_id AS player_id,
        SUM(bos.at_bats)       AS at_bats,
        SUM(bos.hits)          AS hits,
        SUM(bos.runs_scored)   AS runs_scored,
        SUM(bos.rbi)           AS rbi,
        SUM(bos.home_runs)     AS home_runs
FROM stats s
JOIN baseball_offensive_stats bos
    ON bos.id = s.stat_repository_id
WHERE s.stat_holder_type = 'persons'
    AND s.stat_repository_type = 'baseball_offensive_stats'
    AND s.context = 'season-regular'
GROUP BY s.stat_holder_id
) off ON off.player_id = p.id
JOIN (
SELECT s.stat_holder_id AS player_id,
        SUM(cps.events_played) AS events_played
FROM stats s
JOIN core_person_stats cps
    ON cps.id = s.stat_repository_id
WHERE s.stat_holder_type = 'persons'
    AND s.stat_repository_type = 'core_person_stats'
    AND s.context = 'season-regular'
GROUP BY s.stat_holder_id
) core ON core.player_id = p.id
LEFT JOIN (
SELECT s.stat_holder_id AS player_id,
        SUM(bds.putouts)  AS putouts,
        SUM(bds.assists)  AS assists,
        SUM(bds.errors)   AS errors
FROM stats s
JOIN baseball_defensive_stats bds
    ON bds.id = s.stat_repository_id
WHERE s.stat_holder_type = 'persons'
    AND s.stat_repository_type = 'baseball_defensive_stats'
    AND s.context = 'season-regular'
GROUP BY s.stat_holder_id
) def ON def.player_id = p.id
WHERE core.events_played >= 10
AND off.at_bats >= 50
GROUP BY
p.id, core.events_played,
off.at_bats, off.hits, off.runs_scored, off.rbi, off.home_runs,
def.putouts, def.assists, def.errors
ORDER BY batting_average DESC, games_played DESC;
"""


DECIMAL_TOLERANCE = 0.001


def _rows_match_001(actual: tuple[Any, ...], expected: tuple[Any, ...]) -> bool:
    """Compare rows with 0.001 tolerance for decimals/floats (matches mcpmark verify.py)."""
    if len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected, strict=True):
        if isinstance(a, (Decimal, float)) and isinstance(e, (Decimal, float, int)):
            if abs(float(a) - float(e)) > DECIMAL_TOLERANCE:
                return False
        elif hasattr(a, "strftime") and hasattr(e, "strftime"):
            if str(a) != str(e):
                return False
        elif a != e:
            return False
    return True


class BaseballPlayerAnalysisTask(PostgresTask):
    """Task: create baseball_player_analysis table in the sports database (sportsdb schema)."""

    name = "baseball_player_analysis"
    goal = """Create a table called **baseball_player_analysis** that consolidates
baseball player performance data from the sports database.

## Your Task

Create the `baseball_player_analysis` table with the exact structure below and
populate it from the existing tables: **persons**, **display_names**, **stats**,
**baseball_offensive_stats**, **core_person_stats**, **baseball_defensive_stats**.

### Table Structure

- **player_id** (INTEGER, NOT NULL) — Player identifier
- **player_name** (VARCHAR(255), NOT NULL) — Player's full name
- **team_name** (VARCHAR(255)) — Set to 'Unknown' for all players
- **games_played** (INTEGER) — Number of games/events the player participated in
- **at_bats** (INTEGER) — Total at-bats
- **hits** (INTEGER) — Total hits
- **runs_scored** (INTEGER) — Total runs scored
- **rbi** (INTEGER) — Total runs batted in
- **home_runs** (INTEGER) — Total home runs
- **batting_average** (DECIMAL) — hits/at_bats (handle division by zero)
- **defensive_games** (INTEGER) — Same as games_played
- **putouts** (INTEGER) — Total putouts
- **assists** (INTEGER) — Total assists
- **errors** (INTEGER) — Total errors
- **fielding_percentage** (DECIMAL) — (putouts + assists) / (putouts + assists + errors);
  handle division by zero

### Data Requirements

Include only players that meet ALL of:

- Regular season statistics only (`context = 'season-regular'` in stats)
- At least 10 games/events
- At least 50 at-bats
- Valid name (non-empty full_name in display_names)

### Important Notes

- Use 0 or appropriate default for NULLs in calculations.
- Do NOT use ROUND — keep full precision for batting_average and fielding_percentage.
- Sort results by **batting_average DESC**, then **games_played DESC**.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.SPORTS)
        self.evaluators = (
            SqlResultMatches(
                BASEBALL_PLAYER_QUERY,
                expected_query=BASEBALL_PLAYER_EXPECTED,
                rows_match_fn=_rows_match_001,
            ),
        )
