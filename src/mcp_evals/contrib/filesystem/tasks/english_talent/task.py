"""English Talent task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import ExpectedStudents, FileFormat, StudentCount


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

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("qualified_students.txt"),
            FileFormat(),
            StudentCount(),
            ExpectedStudents(),
        )
