"""English Talent task for filesystem domain."""

from pathlib import Path


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
