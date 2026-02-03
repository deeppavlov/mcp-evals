"""English Talent task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected students from answer.md
EXPECTED_STUDENTS = {
    "James Smith": {"id": "20177389", "email": "james.smith30@outlook.com"},
    "Ava Lopez": {"id": "20166998", "email": "ava.lopez67@outlook.com"},
    "James Anderson": {"id": "20153606", "email": "james.anderson71@yahoo.com"},
    "Benjamin Anderson": {"id": "20136681", "email": "benjamin.anderson37@qq.com"},
    "Sarah Wilson": {"id": "20158819", "email": "sarah.wilson96@outlook.com"},
    "Isabella Davis": {"id": "20101701", "email": "isabella.davis89@gmail.com"},
    "James Moore": {"id": "20188937", "email": "james.moore62@gmail.com"},
    "Harper Williams": {"id": "20157943", "email": "harper.williams38@163.com"},
    "Noah Smith": {"id": "20132669", "email": "noah.smith45@163.com"},
    "Emma Thomas": {"id": "20109144", "email": "emma.thomas68@163.com"},
    "Mary Brown": {"id": "20199583", "email": "mary.brown27@yahoo.com"},
    "John Jones": {"id": "20201800", "email": "john.jones46@gmail.com"},
    "Mia Anderson": {"id": "20162542", "email": "mia.anderson3@outlook.com"},
    "Barbara Davis": {"id": "20126203", "email": "barbara.davis67@163.com"},
    "Thomas Brown": {"id": "20119528", "email": "thomas.brown43@163.com"},
    "Susan Anderson": {"id": "20148778", "email": "susan.anderson16@163.com"},
    "Mary Garcia": {"id": "20174369", "email": "mary.garcia58@gmail.com"},
    "Richard Wilson": {"id": "20174207", "email": "richard.wilson39@outlook.com"},
    "Joseph Lopez": {"id": "20191265", "email": "joseph.lopez93@yahoo.com"},
}

EXPECTED_STUDENT_COUNT = 19


def parse_qualified_students_file(work_dir: Path) -> list[dict[str, str]]:
    """Parse the qualified_students.txt file and return structured data."""
    answer_file = work_dir / "qualified_students.txt"

    try:
        content = answer_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        students: list[dict[str, str]] = []
        current_line = 0

        while current_line < len(lines):
            if not lines[current_line].strip():
                current_line += 1
                continue

            name_line = lines[current_line].strip()
            id_line = lines[current_line + 1].strip()
            email_line = lines[current_line + 2].strip()

            name = name_line.replace("name: ", "").strip()
            student_id = id_line.replace("id: ", "").strip()
            email = email_line.replace("email: ", "").strip()

            students.append({"name": name, "id": student_id, "email": email})

            current_line += 4

    except (OSError, UnicodeDecodeError):
        return []
    else:
        return students


@dataclass
class FileFormat(Evaluator["EnglishTalentTask", AgentRunResult]):
    """Evaluator that checks qualified_students.txt file has correct format."""

    def _validate_student_entry(self, lines: list[str], current_line: int) -> EvaluatorOutput | None:
        """Validate a single student entry."""
        if current_line + 2 >= len(lines):
            return EvaluationReason(
                value=0.0,
                reason=f"Incomplete student entry at line {current_line + 1}",
            )

        if not lines[current_line].strip().startswith("name: "):
            return EvaluationReason(
                value=0.0,
                reason=f"Invalid name line format at line {current_line + 1}: {lines[current_line]}",
            )

        if not lines[current_line + 1].strip().startswith("id: "):
            return EvaluationReason(
                value=0.0,
                reason=f"Invalid id line format at line {current_line + 2}: {lines[current_line + 1]}",
            )

        if not lines[current_line + 2].strip().startswith("email: "):
            return EvaluationReason(
                value=0.0,
                reason=f"Invalid email line format at line {current_line + 3}: {lines[current_line + 2]}",
            )

        return None

    def _validate_format(self, lines: list[str]) -> EvaluatorOutput | None:
        """Validate file format."""
        if not lines:
            return EvaluationReason(value=0.0, reason="File is empty")

        current_line = 0
        student_count = 0

        while current_line < len(lines):
            if not lines[current_line].strip():
                current_line += 1
                continue

            error = self._validate_student_entry(lines, current_line)
            if error is not None:
                return error

            student_count += 1
            current_line += 3

            if current_line < len(lines) and lines[current_line].strip():
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing blank line separator after student {student_count}",
                )

            current_line += 1

        if student_count == 0:
            return EvaluationReason(value=0.0, reason="No valid student entries found")

        return None

    async def evaluate(self, ctx: EvaluatorContext["EnglishTalentTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the qualified_students.txt file has the correct format."""
        task = ctx.inputs
        answer_file = task.work_dir / "qualified_students.txt"

        try:
            content = answer_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            error = self._validate_format(lines)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading qualified students file: {e}")

        return 1.0


@dataclass
class StudentCount(Evaluator["EnglishTalentTask", AgentRunResult]):
    """Evaluator that checks exactly 19 students are found."""

    async def evaluate(self, ctx: EvaluatorContext["EnglishTalentTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that exactly 19 students are found."""
        task = ctx.inputs

        students = parse_qualified_students_file(task.work_dir)

        if not students:
            return EvaluationReason(value=0.0, reason="Failed to parse qualified students file")

        if len(students) != EXPECTED_STUDENT_COUNT:
            return EvaluationReason(
                value=0.0,
                reason=f"Expected {EXPECTED_STUDENT_COUNT} students, but found {len(students)}",
            )

        return 1.0


@dataclass
class ExpectedStudents(Evaluator["EnglishTalentTask", AgentRunResult]):
    """Evaluator that checks all expected students are present with correct details."""

    async def evaluate(self, ctx: EvaluatorContext["EnglishTalentTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all expected students are present with correct details."""
        task = ctx.inputs

        students = parse_qualified_students_file(task.work_dir)

        if not students:
            return EvaluationReason(value=0.0, reason="Failed to parse qualified students file")

        found_students = {student["name"] for student in students}

        missing_students = set(EXPECTED_STUDENTS.keys()) - found_students
        if missing_students:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing expected students: {sorted(missing_students)}",
            )

        unexpected_students = found_students - set(EXPECTED_STUDENTS.keys())
        if unexpected_students:
            return EvaluationReason(
                value=0.0,
                reason=f"Unexpected students found: {sorted(unexpected_students)}",
            )

        for student in students:
            expected = EXPECTED_STUDENTS[student["name"]]
            if student["id"] != expected["id"]:
                return EvaluationReason(
                    value=0.0,
                    reason=(f"ID mismatch for {student['name']}: expected {expected['id']}, got {student['id']}"),
                )
            if student["email"] != expected["email"]:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Email mismatch for {student['name']}: expected {expected['email']}, got {student['email']}"
                    ),
                )

        return 1.0


class EnglishTalentTask(FilesystemTask):
    """Task for recruiting students proficient in English.

    The agent must:
    1. Select students with S or A grade in recommendation_letter.txt
    2. Select students with TOEFL score ≥ 100
    3. Compile names, ids, and emails into qualified_students.txt
    4. Find exactly 19 qualified students
    """

    name = "english_talent"
    goal = """Please use FileSystem tools to finish the following task:

We are now recruiting students proficient in English to be responsible for the school's English media operations. \
To contact with students, from the total of 150 students, select those who **meet both of the following criteria**:

1. Rated **S** or **A** grade level in `recommendation_letter.txt` by their teachers.
2. TOEFL score in the basic info is **higher than or equal to 100**.

Please compile all their names, ids and emails into a `qualified_students.txt` file, with the format:

    name: xxx
    id: xxx
    email: xxx

Each person's information should occupy three lines, with one blank line between each block.

### Expected Output

- File name: `qualified_students.txt`
- Format: Three lines per student (name, id, email)
- Blank line separator between students
- Exactly 19 qualified students should be found
- All students must meet both criteria (S/A recommendation AND TOEFL ≥100)"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("qualified_students.txt"),
            FileFormat(),
            StudentCount(),
            ExpectedStudents(),
        )
