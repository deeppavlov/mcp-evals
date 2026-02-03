"""Grade-Based Score task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import GradeSummaryContent, GradeSummaryExists, GradeSummaryReadable, ThreeSubjectsPresent


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
    goal = """Please use FileSystem tools to finish the following task:

### Simple Grade Calculation

1. Read Student Data:
* Process all student basic_info.txt files from the database
* Extract scores for Chinese, Math, and English subjects

2. Calculate Basic Grades:
* Use simple grade scale: A (90+), B (80-89), C (70-79), D (60-69), F (<60)
* Apply this same scale to all subjects

### Generate Output Files

1. Create student_grades.csv:
* Columns: student_id, name, chinese_score, chinese_grade, math_score, math_grade, english_score, english_grade
* Must contain exactly each students
* Each students one row

2. Create grade_summary.txt:
* Total number of students processed
* Number of A's, B's, C's, D's, and F's for each subject
* Simple count of students with passing grades (A, B, C) vs failing grades (D, F) for each subjects

### Expected Output

- Files: `student_grades.csv` and `grade_summary.txt`
- 150 students processed
- Correct grade distribution statistics
- Chinese: 42A, 37B, 43C, 28D, Pass:122, Fail:28
- Math: 31A, 38B, 47C, 34D, Pass:116, Fail:34
- English: 32A, 38B, 38C, 41D, 1F, Pass:108, Fail:42"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            GradeSummaryExists(),
            GradeSummaryReadable(),
            ThreeSubjectsPresent(),
            GradeSummaryContent(),
        )
