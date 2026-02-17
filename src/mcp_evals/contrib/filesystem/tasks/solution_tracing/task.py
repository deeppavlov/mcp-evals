"""Solution Tracing task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import CSVContentMatches, CSVFormat, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import EXPECTED_COLUMN_COUNT, EXPECTED_DATA, EXPECTED_HEADER_COLUMNS
from .custom_evaluators import DataAccuracy


class SolutionTracingTask(FilesystemTask):
    """Task for tracing solutions in legal documents.

    The agent must:
    1. Focus on clauses 4.6, 4.16, 6.8, 6.16 in v5-9
    2. Determine who first proposed the idea that led to final solution
    3. Determine in which version's comment it appeared
    4. Generate tracing.csv with version_number and name for each clause
    """

    name = "solution_tracing"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("tracing.csv"),
            CSVFormat("tracing.csv", expected_columns=EXPECTED_COLUMN_COUNT),
            CSVContentMatches(
                file_path="tracing.csv",
                expected_data=EXPECTED_DATA,
                expected_header_columns=EXPECTED_HEADER_COLUMNS,
                expected_column_count=EXPECTED_COLUMN_COUNT,
                header_start_index=1,
            ),
            DataAccuracy(),
        )
