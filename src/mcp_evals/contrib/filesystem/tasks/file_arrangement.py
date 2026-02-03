"""File Arrangement task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Required folders
REQUIRED_FOLDERS = ["work", "life", "archives", "temp", "others"]

# Required files in each folder
REQUIRED_FILE_MAPPING = {
    "work": [
        "client_list.csv",
        "timesheet.csv",
        "experiment_results.txt",
        "budget_tracker.csv",
        "expenses.csv",
    ],
    "life": [
        "contacts.csv",
        "budget.csv",
        "fitness_log.csv",
        "price_comparisons.csv",
        "book_list.txt",
        "bookmark_export.txt",
        "emergency_contacts.txt",
    ],
    "archives": [
        "backup_contacts.csv",
        "tax_documents_2022.csv",
        "correspondence_2023.txt",
        "tax_info_2023.csv",
    ],
    "temp": [
        "test_data.csv",
        "draft_letter.txt",
    ],
}

# All required files (for duplicate checking)
ALL_REQUIRED_FILES = [
    "client_list.csv",
    "timesheet.csv",
    "experiment_results.txt",
    "budget_tracker.csv",
    "contacts.csv",
    "budget.csv",
    "expenses.csv",
    "fitness_log.csv",
    "price_comparisons.csv",
    "book_list.txt",
    "bookmark_export.txt",
    "emergency_contacts.txt",
    "backup_contacts.csv",
    "tax_documents_2022.csv",
    "correspondence_2023.txt",
    "tax_info_2023.csv",
    "test_data.csv",
    "draft_letter.txt",
]


@dataclass
class FolderStructure(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks all required folders exist."""

    async def evaluate(self, ctx: EvaluatorContext["FileArrangementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required folders exist."""
        task = ctx.inputs

        missing_folders = []
        for folder in REQUIRED_FOLDERS:
            folder_path = task.work_dir / folder
            if not folder_path.exists() or not folder_path.is_dir():
                missing_folders.append(folder)

        if missing_folders:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required folders: {missing_folders}",
            )

        return 1.0


@dataclass
class WorkFolderFiles(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks work folder contains required files."""

    async def evaluate(self, ctx: EvaluatorContext["FileArrangementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that work folder contains the required files."""
        task = ctx.inputs
        work_dir = task.work_dir / "work"

        missing_files = []
        for file_name in REQUIRED_FILE_MAPPING["work"]:
            file_path = work_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required files in work/ folder: {missing_files}",
            )

        return 1.0


@dataclass
class LifeFolderFiles(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks life folder contains required files."""

    async def evaluate(self, ctx: EvaluatorContext["FileArrangementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that life folder contains the required files."""
        task = ctx.inputs
        life_dir = task.work_dir / "life"

        missing_files = []
        for file_name in REQUIRED_FILE_MAPPING["life"]:
            file_path = life_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required files in life/ folder: {missing_files}",
            )

        return 1.0


@dataclass
class ArchivesFolderFiles(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks archives folder contains required files."""

    async def evaluate(self, ctx: EvaluatorContext["FileArrangementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that archives folder contains the required files."""
        task = ctx.inputs
        archives_dir = task.work_dir / "archives"

        missing_files = []
        for file_name in REQUIRED_FILE_MAPPING["archives"]:
            file_path = archives_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required files in archives/ folder: {missing_files}",
            )

        return 1.0


@dataclass
class TempFolderFiles(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks temp folder contains required files."""

    async def evaluate(self, ctx: EvaluatorContext["FileArrangementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that temp folder contains the required files."""
        task = ctx.inputs
        temp_dir = task.work_dir / "temp"

        missing_files = []
        for file_name in REQUIRED_FILE_MAPPING["temp"]:
            file_path = temp_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required files in temp/ folder: {missing_files}",
            )

        return 1.0


@dataclass
class OthersFolderExists(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks others folder exists and can contain any files."""

    async def evaluate(self, ctx: EvaluatorContext["FileArrangementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that others folder exists and can contain any files."""
        task = ctx.inputs
        others_dir = task.work_dir / "others"

        if not others_dir.exists() or not others_dir.is_dir():
            return EvaluationReason(value=0.0, reason="others/ folder not found")

        return 1.0


@dataclass
class RequiredFilesInCorrectFolders(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks all 18 required files are in their correct designated folders."""

    async def evaluate(self, ctx: EvaluatorContext["FileArrangementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 18 required files are in their correct designated folders."""
        task = ctx.inputs

        missing_files = []
        for folder, files in REQUIRED_FILE_MAPPING.items():
            folder_path = task.work_dir / folder
            for file_name in files:
                file_path = folder_path / file_name
                if not file_path.exists():
                    missing_files.append(f"{folder}/{file_name}")

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required files: {missing_files}",
            )

        return 1.0


@dataclass
class NoDuplicateRequiredFiles(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks the 18 required files are not duplicated across folders."""

    async def evaluate(self, ctx: EvaluatorContext["FileArrangementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the 18 required files are not duplicated across folders."""
        task = ctx.inputs

        file_locations: dict[str, str] = {}
        duplicates = []

        for folder in REQUIRED_FOLDERS:
            folder_path = task.work_dir / folder
            if folder_path.exists() and folder_path.is_dir():
                try:
                    for file_path in folder_path.iterdir():
                        if file_path.is_file() and file_path.name in ALL_REQUIRED_FILES:
                            if file_path.name in file_locations:
                                duplicates.append(
                                    f"{file_path.name} (in {file_locations[file_path.name]} and {folder}/)",
                                )
                            else:
                                file_locations[file_path.name] = f"{folder}/"
                except (OSError, PermissionError):
                    continue

        if duplicates:
            return EvaluationReason(
                value=0.0,
                reason=f"Duplicate required files found: {duplicates}",
            )

        return 1.0


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
