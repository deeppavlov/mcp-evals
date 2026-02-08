"""Individual Comments task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import CSVContentMatches, CSVFormat, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import EXPECTED_COLUMN_COUNT, EXPECTED_DATA, EXPECTED_HEADER_COLUMNS
from .custom_evaluators import DataAccuracy


class IndividualCommentsTask(FilesystemTask):
    """Task for counting individual comments by person and clause.

    The agent must:
    1. Count comments by Bill Harvey, Michelle Jackson, David Russel, Tony Taylor
    2. Count comments in clauses 1.1, 1.3, 4.6, 4.16, 6.8, 6.16
    3. Focus on versions 5-8
    4. Generate individual_comment.csv with correct format
    """

    name = "individual_comments"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("individual_comment.csv"),
            CSVFormat("individual_comment.csv", expected_columns=EXPECTED_COLUMN_COUNT),
            CSVContentMatches(
                file_path="individual_comment.csv",
                expected_data=EXPECTED_DATA,
                expected_header_columns=EXPECTED_HEADER_COLUMNS,
                expected_column_count=EXPECTED_COLUMN_COUNT,
                header_start_index=1,
            ),
            DataAccuracy(),
        )
