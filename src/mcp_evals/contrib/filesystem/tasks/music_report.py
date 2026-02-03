"""Music Report task for filesystem domain."""

from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileContentStructure, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected data from MCP Universe verification
EXPECTED_SONGS = [
    {"song_name": "晴天", "popularity_score": 2.576},
    {"song_name": "七里香", "popularity_score": 2.488},
    {"song_name": "江南", "popularity_score": 2.488},
    {"song_name": "夜曲", "popularity_score": 2.448},
    {"song_name": "一千年以后", "popularity_score": 2.44},
    {"song_name": "稻香", "popularity_score": 2.376},
    {"song_name": "青花瓷", "popularity_score": 2.336},
    {"song_name": "不为谁而作的歌", "popularity_score": 2.32},
    {"song_name": "学不会", "popularity_score": 2.304},
    {"song_name": "小酒窝", "popularity_score": 2.264},
    {"song_name": "可惜没如果", "popularity_score": 2.248},
    {"song_name": "修炼爱情", "popularity_score": 2.24},
    {"song_name": "背对背拥抱", "popularity_score": 2.24},
    {"song_name": "爱笑的眼睛", "popularity_score": 2.232},
    {"song_name": "她说", "popularity_score": 2.216},
    {"song_name": "简单爱", "popularity_score": 1.952},
    {"song_name": "龙卷风", "popularity_score": 1.936},
    {"song_name": "双截棍", "popularity_score": 1.92},
    {"song_name": "可爱女人", "popularity_score": 1.912},
    {"song_name": "星晴", "popularity_score": 1.896},
]

EXPECTED_TOP_5 = ["晴天", "七里香", "江南", "夜曲", "一千年以后"]


class SongRankingFormat(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks lines 1-20 have correct song:score format."""

    async def evaluate(self, ctx: EvaluatorContext["MusicReportTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: C901, PLR0911
        """Verify that lines 1-20 contain songs with scores in correct format."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            # Check lines 1-20 (index 0-19)
            for i in range(20):
                if i >= len(lines):
                    return EvaluationReason(value=0.0, reason=f"Line {i + 1} is missing")

                line = lines[i].strip()
                if not line:
                    return EvaluationReason(value=0.0, reason=f"Line {i + 1} is empty")

                # Check format: songname:popularity_score
                if ":" not in line:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i + 1} missing colon separator: '{line}'",
                    )

                parts = line.split(":", 1)
                if len(parts) != 2:  # noqa: PLR2004
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i + 1} has incorrect format: '{line}'",
                    )

                song_name, score_str = parts

                if not song_name.strip():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i + 1} has empty song name: '{line}'",
                    )

                try:
                    score = float(score_str.strip())
                    if score < 0 or score > 5:  # noqa: PLR2004
                        return EvaluationReason(
                            value=0.0,
                            reason=f"Line {i + 1} has invalid score range: {score}",
                        )
                except ValueError:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i + 1} has invalid score format: '{score_str}'",
                    )

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking song ranking format: {e}",
            )
        else:
            return 1.0


class SongRankingOrder(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks songs are ranked by popularity score in descending order."""

    async def evaluate(self, ctx: EvaluatorContext["MusicReportTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that songs are ranked by popularity score in descending order."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            scores = []
            for i in range(20):
                if i >= len(lines):
                    return EvaluationReason(value=0.0, reason=f"Line {i + 1} is missing")

                line = lines[i].strip()
                parts = line.split(":", 1)
                score = float(parts[1].strip())
                scores.append(score)

            # Check if scores are in descending order, allowing equal scores to be adjacent
            for i in range(1, len(scores)):
                if scores[i] > scores[i - 1]:
                    msg = f"Scores not in descending order: {scores[i - 1]} < {scores[i]} at line {i + 1}"
                    return EvaluationReason(value=0.0, reason=msg)

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking song ranking order: {e}",
            )
        else:
            return 1.0


class SongNamesMatchExpected(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks all expected song names are present."""

    async def evaluate(self, ctx: EvaluatorContext["MusicReportTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all expected song names are present in the ranking."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            found_songs = []
            for i in range(20):
                if i >= len(lines):
                    break
                line = lines[i].strip()
                song_name = line.split(":", 1)[0].strip()
                found_songs.append(song_name)

            # Check if all expected songs are present
            missing_songs = [
                expected_song["song_name"]
                for expected_song in EXPECTED_SONGS
                if expected_song["song_name"] not in found_songs
            ]

            if missing_songs:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected songs: {missing_songs}",
                )

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking song names: {e}",
            )
        else:
            return 1.0


class PopularityScoresMatchExpected(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks popularity scores match expected values."""

    async def evaluate(self, ctx: EvaluatorContext["MusicReportTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that popularity scores match the expected values."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            score_errors = []
            for i in range(20):
                if i >= len(lines):
                    break

                line = lines[i].strip()
                parts = line.split(":", 1)
                song_name = parts[0].strip()
                actual_score = float(parts[1].strip())

                # Find expected score for this song
                expected_score: float | None = None
                for expected_song in EXPECTED_SONGS:
                    if expected_song["song_name"] == song_name:
                        score_value = expected_song["popularity_score"]
                        expected_score = float(score_value) if isinstance(score_value, (int, float, str)) else None
                        break

                if expected_score is not None and abs(actual_score - expected_score) > 0.001:  # noqa: PLR2004
                    msg = f"{song_name}: expected {expected_score}, got {actual_score}"
                    score_errors.append(msg)

            if score_errors:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Score mismatches: {score_errors}",
                )

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking popularity scores: {e}",
            )
        else:
            return 1.0


class Top5Songs(Evaluator["MusicReportTask", AgentRunResult]):
    """Evaluator that checks lines 21-25 contain top 5 song names."""

    async def evaluate(self, ctx: EvaluatorContext["MusicReportTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: C901, PLR0911
        """Verify that lines 21-25 contain the top 5 song names."""
        task = ctx.inputs

        report_file = task.work_dir / "music" / "music_analysis_report.txt"

        if not report_file.exists():
            return EvaluationReason(value=0.0, reason="Report file does not exist")

        try:
            content = report_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            # Check lines 21-25 (index 20-24)
            found_top_5 = []
            for i in range(5):
                line_num = i + 21
                if i + 20 >= len(lines):
                    return EvaluationReason(value=0.0, reason=f"Line {line_num} is missing")

                line = lines[i + 20].strip()

                if not line:
                    return EvaluationReason(value=0.0, reason=f"Line {line_num} is empty")

                if ":" in line:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {line_num} should not contain colon: '{line}'",
                    )

                found_top_5.append(line)

            # Check if all expected top 5 songs are present
            missing_songs = [expected_song for expected_song in EXPECTED_TOP_5 if expected_song not in found_top_5]

            if missing_songs:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected top 5 songs: {missing_songs}",
                )

            # Check if the order is valid (allowing equal scores to be swapped)
            # Since 七里香 and 江南 both have score 2.488, they can be in either order
            valid_orders = [
                ["晴天", "七里香", "江南", "夜曲", "一千年以后"],  # Original order
                ["晴天", "江南", "七里香", "夜曲", "一千年以后"],  # Swapped 七里香 and 江南
            ]

            order_valid = False
            for valid_order in valid_orders:
                if found_top_5 == valid_order:
                    order_valid = True
                    break

            if not order_valid:
                msg = f"Top 5 songs order is invalid. Found: {found_top_5}, Expected one of: {valid_orders}"
                return EvaluationReason(value=0.0, reason=msg)

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking top 5 songs: {e}",
            )
        else:
            return 1.0


class MusicReportTask(FilesystemTask):
    """Task for analyzing music files and generating a popularity report.

    The agent must:
    1. Read song information from jay_chou/ and jj_lin/ directories
    2. Calculate popularity scores using the specified formula
    3. Generate music_analysis_report.txt with ranked songs and top 5 list
    """

    name = "music_report"
    goal = """Please use FileSystem tools to finish the following task:

### 1. Data Loading

- Read and extract song information from `jay_chou/`
- Read and extract song information from `jj_lin/`

### 2. Popularity Score Calculation

For each songs, calculate popularity scores using this formula (keep 3 decimal places):

```
popularity_score = (rating x 0.4) + (play_count_normalized x 0.4) + (year_factor x 0.2)

Where:
- rating: song rating (1-5 scale)
- play_count_normalized: play_count / 250 (0-1 scale)
- year_factor: (2025 - release_year) / 25 (recency bonus)
```

### 3. Generate Analysis Report

Create a file named `music_analysis_report.txt` in the `music/` folder with the following exact format:

**Lines 1-20**: Each line contains one song in format `songname:popularity_score`

- Sort songs by popularity_score in descending order (highest first)
- Use exact song names as they appear in the source files
- Include all 20 songs from both artists

**Lines 21-25**: Top 5 song names only (one per line)

- List the top 5 songs by popularity_score
- No scores, just song names
- One song name per line

**Important**: The file must contain exactly 25 lines with no additional content, headers, or formatting."""

    def __init__(self, work_dir: Path, fixute: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixute)

        self.evaluators = (
            FileExists("music/music_analysis_report.txt"),
            FileContentStructure("music/music_analysis_report.txt", expected_lines=25),
            SongRankingFormat(),
            SongRankingOrder(),
            SongNamesMatchExpected(),
            PopularityScoresMatchExpected(),
            Top5Songs(),
        )
