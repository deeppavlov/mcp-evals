"""English Talent task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import ExpectedStudents, FileFormat, StudentCount


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
