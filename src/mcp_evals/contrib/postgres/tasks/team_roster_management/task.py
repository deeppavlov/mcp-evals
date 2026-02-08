"""Team roster management in the sports database (mcpmark parity)."""

from decimal import Decimal
from typing import Any

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

DECIMAL_TOLERANCE = 0.001


def rows_match_001(actual: tuple[Any, ...], expected: tuple[Any, ...]) -> bool:
    """Compare rows with 0.001 tolerance for Decimal and float (mcpmark verify parity)."""
    if len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected, strict=True):
        if isinstance(a, Decimal) and isinstance(e, (Decimal, float, int)):
            if abs(float(a) - float(e)) > DECIMAL_TOLERANCE:
                return False
        elif isinstance(a, float) and isinstance(e, (Decimal, float, int)):
            if abs(a - float(e)) > DECIMAL_TOLERANCE:
                return False
        elif hasattr(a, "strftime") and hasattr(e, "strftime"):
            if str(a) != str(e):
                return False
        elif a != e:
            return False
    return True


# Ground truth: player_evaluation (from stats, baseball_offensive_stats, person_event_metadata, injury_phases)
PLAYER_EVALUATION_QUERY = """
SELECT person_id, batting_avg, home_runs, rbis, games_played, performance_score
FROM player_evaluation
ORDER BY person_id
"""
PLAYER_EVALUATION_EXPECTED = """
WITH initial_players AS (
    SELECT
        s.stat_holder_id AS person_id,
        SUM(bos.hits)      AS total_hits,
        SUM(bos.at_bats)   AS total_at_bats,
        CASE
            WHEN SUM(bos.at_bats) > 0
            THEN 1.0 * SUM(bos.hits) / SUM(bos.at_bats)
            ELSE 0
        END                AS batting_avg,
        SUM(bos.home_runs) AS home_runs,
        SUM(bos.rbi)       AS rbis
    FROM stats s
    JOIN baseball_offensive_stats bos
    ON s.stat_repository_id = bos.id
    WHERE s.stat_holder_type = 'persons'
    AND s.stat_repository_type = 'baseball_offensive_stats'
    GROUP BY s.stat_holder_id
),
game_counts AS (
    SELECT
        person_id,
        COUNT(DISTINCT event_id) AS games_played
    FROM person_event_metadata
    GROUP BY person_id
),
players_with_games AS (
    SELECT
        ip.person_id,
        ip.batting_avg,
        ip.home_runs,
        ip.rbis,
        COALESCE(gc.games_played, 0) AS games_played,
        (ip.batting_avg * 1000)
        + (COALESCE(ip.home_runs, 0) * 5)
        + (COALESCE(ip.rbis, 0) * 2) AS initial_score
    FROM initial_players ip
    LEFT JOIN game_counts gc ON ip.person_id = gc.person_id
    WHERE COALESCE(gc.games_played, 0) >= 10
),
injury_info AS (
    SELECT
        person_id,
        COUNT(*) AS injury_count,
        MAX(CASE WHEN end_date_time IS NULL THEN 1 ELSE 0 END) AS has_active_injury
    FROM injury_phases
    GROUP BY person_id
),
adjusted_scores AS (
    SELECT
        pwg.person_id,
        pwg.batting_avg,
        pwg.home_runs,
        pwg.rbis,
        pwg.games_played,
        GREATEST(
            CASE
                WHEN COALESCE(ii.has_active_injury, 0) = 1 AND COALESCE(ii.injury_count, 0) > 2
                    THEN pwg.initial_score * 0.8 * 0.9
                WHEN COALESCE(ii.has_active_injury, 0) = 1
                    THEN pwg.initial_score * 0.8
                WHEN COALESCE(ii.injury_count, 0) > 2
                    THEN pwg.initial_score * 0.9
                ELSE pwg.initial_score
            END,
            0
        ) AS performance_score
    FROM players_with_games pwg
    LEFT JOIN injury_info ii ON ii.person_id = pwg.person_id
)
SELECT
    person_id,
    batting_avg,
    home_runs,
    rbis,
    games_played,
    performance_score
FROM adjusted_scores
ORDER BY person_id
"""

# Ground truth: player_injury_status (uses player_evaluation + injury_phases)
PLAYER_INJURY_STATUS_QUERY = """
SELECT person_id, injury_count, last_injury_date, current_status
FROM player_injury_status
ORDER BY person_id
"""
PLAYER_INJURY_STATUS_EXPECTED = """
WITH player_list AS (
    SELECT DISTINCT person_id
    FROM player_evaluation
),
injury_counts AS (
    SELECT
        person_id,
        COUNT(*) as injury_count,
        MAX(start_date_time::date) as last_injury_date,
        MAX(CASE WHEN end_date_time IS NULL THEN 1 ELSE 0 END) as has_active_injury
    FROM injury_phases
    GROUP BY person_id
)
SELECT
    pl.person_id,
    COALESCE(ic.injury_count, 0) as injury_count,
    ic.last_injury_date,
    CASE
        WHEN COALESCE(ic.has_active_injury, 0) = 1 THEN 'injured'
        ELSE 'healthy'
    END as current_status
FROM player_list pl
LEFT JOIN injury_counts ic ON pl.person_id = ic.person_id
ORDER BY pl.person_id
"""

# Ground truth: team_performance_summary (uses player_evaluation + player_injury_status)
TEAM_PERFORMANCE_SUMMARY_QUERY = """
SELECT metric_name, metric_value
FROM team_performance_summary
ORDER BY metric_name
"""
TEAM_PERFORMANCE_SUMMARY_EXPECTED = """
WITH player_data AS (
    SELECT
        COUNT(*) as total_players,
        AVG(batting_avg) as avg_batting_average,
        SUM(home_runs) as total_home_runs,
        AVG(performance_score) as avg_performance_score
    FROM player_evaluation
),
health_data AS (
    SELECT
        SUM(CASE WHEN current_status = 'injured' THEN 1 ELSE 0 END) as injured_count,
        SUM(CASE WHEN current_status = 'healthy' THEN 1 ELSE 0 END) as healthy_count
    FROM player_injury_status
    WHERE person_id IN (SELECT person_id FROM player_evaluation)
)
SELECT metric_name, metric_value::DECIMAL
FROM (
    SELECT 'avg_batting_average' as metric_name, avg_batting_average as metric_value FROM player_data
    UNION ALL
    SELECT 'avg_performance_score', avg_performance_score FROM player_data
    UNION ALL
    SELECT 'healthy_player_count', healthy_count FROM health_data
    UNION ALL
    SELECT 'injured_player_count', injured_count FROM health_data
    UNION ALL
    SELECT 'total_home_runs', total_home_runs FROM player_data
    UNION ALL
    SELECT 'total_players', total_players FROM player_data
) metrics
ORDER BY metric_name
"""


class TeamRosterManagementTask(PostgresTask):
    """Task: implement team roster management operations."""

    name = "team_roster_management"

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.SPORTS)
        self.evaluators = (
            SqlResultMatches(
                PLAYER_EVALUATION_QUERY,
                expected_query=PLAYER_EVALUATION_EXPECTED,
                rows_match_fn=rows_match_001,
            ),
            SqlResultMatches(
                PLAYER_INJURY_STATUS_QUERY,
                expected_query=PLAYER_INJURY_STATUS_EXPECTED,
                rows_match_fn=rows_match_001,
            ),
            SqlResultMatches(
                TEAM_PERFORMANCE_SUMMARY_QUERY,
                expected_query=TEAM_PERFORMANCE_SUMMARY_EXPECTED,
                rows_match_fn=rows_match_001,
            ),
        )
