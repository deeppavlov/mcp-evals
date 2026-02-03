"""Duplicate Name task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected duplicate names from answer.md
EXPECTED_DUPLICATES = {
    "Isabella Smith": ["20132026", "20133697"],
    "Ava Lopez": ["20166564", "20166998"],
    "James Moore": ["20159695", "20188937"],
    "William Taylor": ["20175314", "20189854"],
    "Ethan Wilson": ["20182390", "20196998"],
    "Christopher Taylor": ["20128879", "20187892"],
    "William Anderson": ["20142085", "20146277"],
    "James Anderson": ["20147789", "20153606"],
    "Olivia Jones": ["20189192", "20196896"],
    "Mason Johnson": ["20115252", "20199735"],
    "Benjamin Jackson": ["20153174", "20194160"],
    "John Taylor": ["20194525", "20201385"],
    "Susan Anderson": ["20148778", "20173517"],
    "Christopher Moore": ["20112439", "20146279"],
    "Sarah Wilson": ["20158819", "20204611"],
    "Sarah Brown": ["20104498", "20108742"],
}

EXPECTED_DUPLICATE_COUNT = 16


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


@dataclass
class ExpectedResults(Evaluator["DuplicateNameTask", AgentRunResult]):
    """Evaluator that checks results match expected answer.md content exactly."""

    def _validate_name_presence(self, namesakes: dict[str, dict[str, int | list[str]]]) -> EvaluatorOutput | None:
        """Validate that all expected names are present and no unexpected names exist."""
        for expected_name in EXPECTED_DUPLICATES:
            if expected_name not in namesakes:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected duplicate name: '{expected_name}'",
                )

        for name in namesakes:
            if name not in EXPECTED_DUPLICATES:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Unexpected duplicate name found: '{name}' (not in expected list)",
                )

        return None

    def _validate_name_data(self, name: str, data: dict[str, int | list[str]]) -> EvaluatorOutput | None:
        """Validate data for a single name."""
        expected_ids = set(EXPECTED_DUPLICATES[name])
        ids = data["ids"]
        if not isinstance(ids, list):
            return EvaluationReason(
                value=0.0,
                reason=f"Invalid ids type for '{name}': expected list, got {type(ids).__name__}",
            )
        stated_ids = set(ids)

        if expected_ids != stated_ids:
            return EvaluationReason(
                value=0.0,
                reason=(f"ID mismatch for '{name}'. Expected: {sorted(expected_ids)}, Stated: {sorted(stated_ids)}"),
            )

        if data["count"] != 2:  # noqa: PLR2004
            return EvaluationReason(
                value=0.0,
                reason=f"Count mismatch for '{name}': expected 2, got {data['count']}",
            )

        return None

    def _validate_namesakes(self, namesakes: dict[str, dict[str, int | list[str]]]) -> EvaluatorOutput | None:
        """Validate namesakes against expected data."""
        if len(namesakes) != EXPECTED_DUPLICATE_COUNT:
            reason_msg = f"Expected exactly {EXPECTED_DUPLICATE_COUNT} duplicate names, but found {len(namesakes)}"
            return EvaluationReason(value=0.0, reason=reason_msg)

        error = self._validate_name_presence(namesakes)
        if error is not None:
            return error

        for name, data in namesakes.items():
            error = self._validate_name_data(name, data)
            if error is not None:
                return error

        return None

    async def evaluate(self, ctx: EvaluatorContext["DuplicateNameTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the results match the expected answer.md content exactly."""
        task = ctx.inputs

        namesakes = parse_namesake_file(task.work_dir)

        if not namesakes:
            return EvaluationReason(value=0.0, reason="Failed to parse namesake file")

        error = self._validate_namesakes(namesakes)
        if error is not None:
            return error

        return 1.0


class DuplicateNameTask(FilesystemTask):
    """Task for identifying duplicate names from student database.

    The agent must:
    1. Identify duplicate names from 150 students
    2. Generate namesake.txt with format: name, count, ids
    3. Find exactly 16 duplicate names
    4. Each duplicate name should have exactly 2 student IDs
    """

    name = "duplicate_name"
    goal = """Please use FileSystem tools to finish the following task:

Please help me identify duplicate names from the list of all the 150 students. Do not use python code.
Then generate a `namesake.txt` file to record the results in the following format,
with each group written in three lines:

name: xxx
count: xxx
ids: xxx, xxx, ...

Leave one blank line between every two groups.
If there are multiple duplicates, just list all corresponding IDs in the third line.

### Expected Output

- File name: `namesake.txt`
- Format: Three lines per duplicate name group (name, count, ids)
- Blank line separator between groups
- Exactly 16 duplicate names should be identified
- Each duplicate name should have exactly 2 student IDs"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("namesake.txt"),
            ExpectedResults(),
        )
