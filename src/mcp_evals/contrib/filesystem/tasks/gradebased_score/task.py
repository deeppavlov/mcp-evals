"""Grade-Based Score task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FileReadable
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import GradeSummaryContent, ThreeSubjectsPresent


class GradebasedScoreTask(FilesystemTask):
    """Task for calculating grade-based scores from student database.

    The agent must:
    1. Read all student basic_info.txt files
    2. Extract scores for Chinese, Math, and English
    3. Calculate grades: A (90+), B (80-89), C (70-79), D (60-69), F (<60)
    4. Create student_grades.csv
    5. Create grade_summary.txt with statistics
    """

    name = "gradebased_score"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("grade_summary.txt"),
            FileReadable("grade_summary.txt"),
            ThreeSubjectsPresent(),
            GradeSummaryContent(),
        )
