"""Contact Information task for filesystem domain."""

import csv
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected data from answer.csv
EXPECTED_DATA = [
    {"Name": "John Smith", "Email": "john@email.com", "Phone": "555-0101", "Status": "", "Industry": ""},
    {"Name": "Jane Doe", "Email": "jane@email.com", "Phone": "555-0102", "Status": "", "Industry": ""},
    {"Name": "Bob Johnson", "Email": "bob@email.com", "Phone": "555-0103", "Status": "", "Industry": ""},
    {"Name": "Alice Brown", "Email": "alice@email.com", "Phone": "555-0201", "Status": "Inactive", "Industry": ""},
    {"Name": "Charlie Davis", "Email": "charlie@email.com", "Phone": "555-0202", "Status": "Active", "Industry": ""},
    {"Name": "David Wilson", "Email": "david@email.com", "Phone": "555-0203", "Status": "Inactive", "Industry": ""},
    {"Name": "Acme Corp", "Email": "acme@corp.com", "Phone": "", "Status": "", "Industry": "Technology"},
    {"Name": "Global Inc", "Email": "global@inc.com", "Phone": "", "Status": "", "Industry": "Finance"},
    {"Name": "Local Business", "Email": "local@biz.com", "Phone": "", "Status": "", "Industry": "Retail"},
    {"Name": "Spouse", "Email": "", "Phone": "+1-555-0124", "Status": "", "Industry": ""},
    {"Name": "Parent", "Email": "", "Phone": "+1-555-0125", "Status": "", "Industry": ""},
    {"Name": "Sibling", "Email": "", "Phone": "+1-555-0126", "Status": "", "Industry": ""},
    {"Name": "Primary Doctor", "Email": "", "Phone": "+1-555-0201", "Status": "", "Industry": ""},
    {"Name": "Dentist", "Email": "", "Phone": "+1-555-0202", "Status": "", "Industry": ""},
    {"Name": "Pharmacy", "Email": "", "Phone": "+1-555-0203", "Status": "", "Industry": ""},
]

EXPECTED_NAMES = [
    "John Smith",
    "Jane Doe",
    "Bob Johnson",
    "Alice Brown",
    "Charlie Davis",
    "David Wilson",
    "Acme Corp",
    "Global Inc",
    "Local Business",
    "Spouse",
    "Parent",
    "Sibling",
    "Primary Doctor",
    "Dentist",
    "Pharmacy",
]


@dataclass
class FilesInCorrectLocations(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks files are in correct locations."""

    async def evaluate(self, ctx: EvaluatorContext["ContactInformationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are in the correct locations."""
        task = ctx.inputs
        contact_file = task.work_dir / "contact_info.csv"
        answer_file = task.work_dir / "answer.txt"

        if contact_file.parent != task.work_dir:
            return EvaluationReason(
                value=0.0,
                reason=f"contact_info.csv is not in main directory: {contact_file}",
            )

        if answer_file.parent != task.work_dir:
            return EvaluationReason(
                value=0.0,
                reason=f"answer.txt is not in main directory: {answer_file}",
            )

        return 1.0


@dataclass
class CSVStructure(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks CSV file has correct structure."""

    def _validate_structure(self, rows: list[list[str]]) -> EvaluatorOutput | None:
        """Validate CSV structure and return error if invalid."""
        min_required_rows = 2
        if len(rows) < min_required_rows:
            return EvaluationReason(value=0.0, reason="CSV file has insufficient rows")

        headers = rows[0]
        if not headers:
            return EvaluationReason(value=0.0, reason="CSV file has no headers")

        if headers[0].lower() != "name":
            return EvaluationReason(value=0.0, reason="First column is not 'Name'")

        header_lower = [h.lower() for h in headers]
        if "email" not in header_lower:
            return EvaluationReason(value=0.0, reason="'Email' column not found")

        if "phone" not in header_lower:
            return EvaluationReason(value=0.0, reason="'Phone' column not found")

        return None

    async def evaluate(self, ctx: EvaluatorContext["ContactInformationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the CSV file has the correct structure."""
        task = ctx.inputs
        contact_file = task.work_dir / "contact_info.csv"

        try:
            with contact_file.open("r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            error = self._validate_structure(rows)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading CSV file: {e}")

        return 1.0


@dataclass
class CSVContentAccuracy(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks CSV content contains all required data."""

    def _check_duplicate(self, row_name: str, found_entries: set[str]) -> EvaluatorOutput | None:
        """Check for duplicate entries."""
        if row_name in found_entries:
            return EvaluationReason(
                value=0.0,
                reason=f"Duplicate name found: '{row_name}'",
            )
        return None

    def _check_row_columns(
        self, row_name: str, row: dict[str, str], expected: dict[str, str]
    ) -> EvaluatorOutput | None:
        """Check that row columns match expected values."""
        for key, expected_value in expected.items():
            if key in row:
                actual_value = row[key] if row[key] else ""
                if actual_value != expected_value:
                    msg = f"Entry '{row_name}', column '{key}': expected '{expected_value}', got '{actual_value}'"
                    return EvaluationReason(value=0.0, reason=msg)
            else:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Entry '{row_name}' missing column '{key}'",
                )
        return None

    async def evaluate(self, ctx: EvaluatorContext["ContactInformationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the CSV content contains all required data."""
        task = ctx.inputs
        contact_file = task.work_dir / "contact_info.csv"

        try:
            with contact_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            expected_dict = {entry["Name"]: entry for entry in EXPECTED_DATA}

            found_entries: set[str] = set()
            for row in rows:
                row_name = row.get("Name", "")
                if not row_name:
                    continue

                if row_name in expected_dict:
                    duplicate_check = self._check_duplicate(row_name, found_entries)
                    if duplicate_check is not None:
                        return duplicate_check

                    found_entries.add(row_name)
                    expected = expected_dict[row_name]

                    column_check = self._check_row_columns(row_name, row, expected)
                    if column_check is not None:
                        return column_check

            if len(found_entries) != len(EXPECTED_DATA):
                missing = set(expected_dict.keys()) - found_entries
                return EvaluationReason(value=0.0, reason=f"Missing entries: {sorted(missing)}")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying CSV content: {e}")

        return 1.0


@dataclass
class CSVDataCompleteness(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks all required data is present and no entries are missing."""

    async def evaluate(self, ctx: EvaluatorContext["ContactInformationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required data is present and no entries are missing."""
        task = ctx.inputs
        contact_file = task.work_dir / "contact_info.csv"

        try:
            with contact_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            actual_names = [row.get("Name", "") for row in rows if row.get("Name")]

            missing_names = set(EXPECTED_NAMES) - set(actual_names)
            if missing_names:
                return EvaluationReason(value=0.0, reason=f"Missing names: {sorted(missing_names)}")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking data completeness: {e}")

        return 1.0


@dataclass
class AnswerContent(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks answer.txt contains correct answer about Charlie Davis."""

    async def evaluate(self, ctx: EvaluatorContext["ContactInformationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer.txt contains the correct answer about Charlie Davis."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip().lower()

            if "dentist" in content:
                return 1.0

            return EvaluationReason(
                value=0.0,
                reason=f"Answer does not contain 'dentist'. Found: '{content}'",
            )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer.txt: {e}")


class ContactInformationTask(FilesystemTask):
    """Task for compiling contact information from all files into a CSV table.

    The agent must:
    1. Scan all files in the directory
    2. Extract contact information for all individuals and organizations
    3. Create contact_info.csv with Name, Email, Phone columns
    4. Answer what is Charlie Davis's job/profession in answer.txt
    """

    name = "contact_information"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

Your task is to compile all contact information from all the files into a single CSV table.
You need to extract all people's contact information and organize it systematically.

### Task Objectives

1. **Scan all files** in the directory
2. **Extract contact information** for all individuals and organizations found
3. **Create a CSV file** named `contact_info.csv` in the main directory
4. **Structure the CSV** with the following columns:
   - First column: Name (required)
   - Second column: Email (required)
   - Third column: Phone (required)
   - Additional columns: Any other contact information types found
5. **Consolidate information** by merging the same types of information into single columns
6. **Leave cells blank** if specific information is not available for a person/organization

### Expected Output

- **File name**: `contact_info.csv`
- **Format**: CSV with headers and data rows

### Reasoning Task

After creating the contact_info.csv file, analyze the data to answer:
**What is Charlie Davis's job/profession?**

Hint: focus on the contact information in contact_info.csv.

Write your answer in a file named `answer.txt` in the main directory.

### Important Notes

- Do not modify any existing files
- Only create the two new files: `contact_info.csv` and `answer.txt`"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("contact_info.csv"),
            FileExists("answer.txt"),
            FilesInCorrectLocations(),
            CSVStructure(),
            CSVContentAccuracy(),
            CSVDataCompleteness(),
            AnswerContent(),
        )
