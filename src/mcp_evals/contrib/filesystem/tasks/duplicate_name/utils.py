"""Helper functions for duplicate_name task."""

from pathlib import Path


def _parse_entry(lines: list[str], current_line: int) -> tuple[tuple[str, dict[str, int | list[str]]] | None, int]:
    """Parse a single entry and return (name, entry dict) or None, and next line index."""
    if current_line + 2 >= len(lines):
        return None, current_line

    name_line = lines[current_line].strip()
    count_line = lines[current_line + 1].strip()
    ids_line = lines[current_line + 2].strip()

    if not name_line.startswith("name: "):
        return None, current_line

    name = name_line.replace("name: ", "").strip()

    if not count_line.startswith("count: "):
        return None, current_line

    count_str = count_line.replace("count: ", "").strip()
    try:
        count = int(count_str)
    except ValueError:
        return None, current_line

    if not ids_line.startswith("ids: "):
        return None, current_line

    ids_str = ids_line.replace("ids: ", "").strip()
    ids = [i.strip() for i in ids_str.split(",")]

    return (name, {"count": count, "ids": ids}), current_line + 4


def parse_namesake_file(work_dir: Path) -> dict[str, dict[str, int | list[str]]]:
    """Parse the namesake.txt file and return structured data."""
    namesake_file = work_dir / "namesake.txt"

    try:
        content = namesake_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        namesakes: dict[str, dict[str, int | list[str]]] = {}
        current_line = 0

        while current_line < len(lines):
            if not lines[current_line].strip():
                current_line += 1
                continue

            result, next_line = _parse_entry(lines, current_line)
            if result is None:
                return {}

            name, entry = result
            namesakes[name] = entry

            current_line = next_line

    except (OSError, UnicodeDecodeError):
        return {}

    return namesakes

