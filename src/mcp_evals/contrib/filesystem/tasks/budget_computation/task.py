"""Budget Computation task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileContentStructure, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import EXPECTED_TOTAL_LINES
from .custom_evaluators import (
    ExpenseEntries,
    FileFormat,
    FilePathsAndCounts,
    IndividualPrices,
    TotalCalculation,
    TotalPrice,
)


class BudgetComputationTask(FilesystemTask):
    """Task for calculating personal life expenses and creating budget summary.

    The agent must:
    1. Locate and analyze all files in the desktop environment
    2. Extract personal life expenses (exclude project/work expenses)
    3. Create total_budget.txt with format file_path;price
    4. Add total sum as the last line
    """

    name = "budget_computation"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("total_budget.txt"),
            FileFormat(),
            FileContentStructure("total_budget.txt", expected_lines=EXPECTED_TOTAL_LINES),
            ExpenseEntries(),
            FilePathsAndCounts(),
            IndividualPrices(),
            TotalPrice(),
            TotalCalculation(),
        )
