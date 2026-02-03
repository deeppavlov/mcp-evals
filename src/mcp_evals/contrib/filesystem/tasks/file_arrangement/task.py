"""File Arrangement task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import (
    ArchivesFolderFiles,
    FolderStructure,
    LifeFolderFiles,
    NoDuplicateRequiredFiles,
    OthersFolderExists,
    RequiredFilesInCorrectFolders,
    TempFolderFiles,
    WorkFolderFiles,
)


class FileArrangementTask(FilesystemTask):
    """Task for organizing files into structured folder system.

    The agent must:
    1. Create folders: work/, life/, archives/, temp/, others/
    2. Move files to their designated locations according to organization scheme
    3. Ensure all 18 required files are in correct folders
    4. Ensure no duplicate required files
    """

    name = "file_arrangement"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You are tasked with organizing files on an AI researcher's desktop into a structured folder system.
You need to create specific folders and move files to their designated locations
according to the provided organization scheme.

### Task Objectives

1. **Create the following folder structure** in the main directory:

   - `work/` - for work, research and projects related files
   - `life/` - for personal life related files
   - `archives/` - for archived files or files with past dates in its file names
   - `temp/` - for temporary files, drafts
   - `others/` - for files that cannot be classified elsewhere

2. **Organize the files** according to these rules:

   **Work folder (5 files)**:
   - client_list.csv
   - timesheet.csv
   - experiment_results.txt
   - budget_tracker.csv
   - expenses.csv

   **Life folder (7 files)**:
   - contacts.csv
   - budget.csv
   - fitness_log.csv
   - price_comparisons.csv
   - book_list.txt
   - bookmark_export.txt
   - emergency_contacts.txt

   **Archives folder (4 files)**:
   - backup_contacts.csv
   - tax_documents_2022.csv
   - correspondence_2023.txt
   - tax_info_2023.csv

   **Temp folder (2 files)**:
   - test_data.csv
   - draft_letter.txt

   **Others folder**:
   - Any other files that don't fit the above categories

### Important Notes

- All files must be moved from their current locations to the specified folders
- The `others/` folder is for files that don't fit the other categories
- Do not modify the contents of any files, only move them to the correct locations
- If you are not sure about which folder it should belongs to,
  you can read the context in the files before making decisions
- **Do not change files' name**"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FolderStructure(),
            WorkFolderFiles(),
            LifeFolderFiles(),
            ArchivesFolderFiles(),
            TempFolderFiles(),
            OthersFolderExists(),
            RequiredFilesInCorrectFolders(),
            NoDuplicateRequiredFiles(),
        )
