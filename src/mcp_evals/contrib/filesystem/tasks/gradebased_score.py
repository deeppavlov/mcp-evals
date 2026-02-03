"""Grade-Based Score task for filesystem domain."""

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected numbers from answer.md
EXPECTED_NUMBERS = [
    150,  # Total students
    42, 37, 43, 28, 122, 28,  # Chinese: A(42), B(37), C(43), D(28), Pass(122), Fail(28)
    31, 38, 47, 34, 116, 34,  # Math: A(31), B(38), C(47), D(34), Pass(116), Fail(34)
    32, 38, 38, 41, 1, 108, 42,  # English: A(32), B(38), C(38), D(41), F(1), Pass(108), Fail(42)
]


def extract_numbers_from_text(text: str) -> list[int]:
    """Extract all numbers from text."""
    numbers = re.findall(r"\d+", text)
    return [int(num) for num in numbers]


@dataclass
class GradeSummaryExists(Evaluator["GradebasedScoreTask", AgentRunResult]):
    """Evaluator that checks grade_summary.txt file exists."""

    async def evaluate(self, ctx: EvaluatorContext["GradebasedScoreTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that grade_summary.txt file exists."""
        task = ctx.inputs
        grade_summary_file = task.work_dir / "grade_summary.txt"

        if not grade_summary_file.exists():
            return EvaluationReason(value=0.0, reason="File 'grade_summary.txt' not found")

        return 1.0


@dataclass
class GradeSummaryReadable(Evaluator["GradebasedScoreTask", AgentRunResult]):
    """Evaluator that checks grade_summary.txt file is readable."""

    async def evaluate(self, ctx: EvaluatorContext["GradebasedScoreTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the grade_summary.txt file is readable."""
        task = ctx.inputs
        grade_summary_file = task.work_dir / "grade_summary.txt"

        try:
            content = grade_summary_file.read_text(encoding="utf-8")
            if not content.strip():
                return EvaluationReason(value=0.0, reason="grade_summary.txt file is empty")
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading grade_summary.txt file: {e}")

        return 1.0


@dataclass
class ThreeSubjectsPresent(Evaluator["GradebasedScoreTask", AgentRunResult]):
    """Evaluator that checks grade_summary.txt contains all three subjects."""

    async def evaluate(self, ctx: EvaluatorContext["GradebasedScoreTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that grade_summary.txt contains all three subjects (case insensitive)."""
        task = ctx.inputs
        grade_summary_file = task.work_dir / "grade_summary.txt"

        try:
            content = grade_summary_file.read_text(encoding="utf-8")

            subjects = ["chinese", "math", "english"]
            missing_subjects = []

            for subject in subjects:
                if subject.lower() not in content.lower():
                    missing_subjects.append(subject)

            if missing_subjects:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing subjects in grade_summary.txt: {missing_subjects}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking subjects: {e}")

        return 1.0


@dataclass
class GradeSummaryContent(Evaluator["GradebasedScoreTask", AgentRunResult]):
    """Evaluator that checks grade_summary.txt contains correct statistics."""

    async def evaluate(self, ctx: EvaluatorContext["GradebasedScoreTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that grade_summary.txt contains the correct statistics from answer.md."""
        task = ctx.inputs
        grade_summary_file = task.work_dir / "grade_summary.txt"

        try:
            content = grade_summary_file.read_text(encoding="utf-8")

            found_numbers = extract_numbers_from_text(content)

            if not found_numbers:
                return EvaluationReason(value=0.0, reason="No numbers found in grade_summary.txt")

            missing_numbers = []
            for expected in EXPECTED_NUMBERS:
                if expected not in found_numbers:
                    missing_numbers.append(expected)

            if missing_numbers:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected numbers: {missing_numbers}",
                )

            # Check if the counts match (each number should appear the expected number of times)
            for expected in EXPECTED_NUMBERS:
                expected_count = EXPECTED_NUMBERS.count(expected)
                found_count = found_numbers.count(expected)
                if found_count < expected_count:
                    return EvaluationReason(
                        value=0.0,
                        reason=(
                            f"Number {expected} appears {found_count} times, "
                            f"expected {expected_count} times"
                        ),
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying grade summary content: {e}")

        return 1.0


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

