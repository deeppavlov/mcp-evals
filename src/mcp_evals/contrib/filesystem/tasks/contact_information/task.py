"""Contact Information task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FileInDirectory
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import AnswerContent, CSVContentAccuracy, CSVDataCompleteness, CSVStructure


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
            FileInDirectory("contact_info.csv", expected_directory=None),
            FileInDirectory("answer.txt", expected_directory=None),
            CSVStructure(),
            CSVContentAccuracy(),
            CSVDataCompleteness(),
            AnswerContent(),
        )
