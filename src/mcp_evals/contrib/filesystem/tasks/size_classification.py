"""Size Classification task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import NoFilesInRoot
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected file classification
EXPECTED_CLASSIFICATION = {
    "small_files": ["random_file_1.txt", "random_file_3.txt"],
    "medium_files": ["random_file_2.txt"],
    "large_files": ["bear.jpg", "sg.jpg", "road.MOV", "bus.MOV", "bridge.jpg"],
}

REQUIRED_DIRS = ["small_files", "medium_files", "large_files"]

# System files to ignore
SYSTEM_FILES = [".DS_Store", "Thumbs.db", ".DS_Store?", "._.DS_Store"]

# Size thresholds
SMALL_FILE_MAX = 299  # < 300 bytes
MEDIUM_FILE_MIN = 300  # 300-700 bytes (inclusive)
MEDIUM_FILE_MAX = 700
LARGE_FILE_MIN = 701  # > 700 bytes

# Size ranges
SIZE_RANGES = {
    "small_files": (0, SMALL_FILE_MAX),
    "medium_files": (MEDIUM_FILE_MIN, MEDIUM_FILE_MAX),
    "large_files": (LARGE_FILE_MIN, float("inf")),
}

TOTAL_EXPECTED_FILES = sum(len(files) for files in EXPECTED_CLASSIFICATION.values())


@dataclass
class DirectoriesExist(Evaluator["SizeClassificationTask", AgentRunResult]):
    """Evaluator that checks all three required directories exist."""

    async def evaluate(self, ctx: EvaluatorContext["SizeClassificationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all three required directories exist."""
        task = ctx.inputs

        for dir_name in REQUIRED_DIRS:
            dir_path = task.work_dir / dir_name
            if not dir_path.exists():
                return EvaluationReason(value=0.0, reason=f"Directory '{dir_name}' not found")

            if not dir_path.is_dir():
                return EvaluationReason(value=0.0, reason=f"'{dir_name}' exists but is not a directory")

        return 1.0


@dataclass
class FileClassification(Evaluator["SizeClassificationTask", AgentRunResult]):
    """Evaluator that checks files are correctly classified into the right directories."""

    async def evaluate(self, ctx: EvaluatorContext["SizeClassificationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are correctly classified into the right directories."""
        task = ctx.inputs

        for dir_name, expected_files in EXPECTED_CLASSIFICATION.items():
            dir_path = task.work_dir / dir_name

            # Check that all expected files are in the directory
            missing_files = []
            for filename in expected_files:
                file_path = dir_path / filename
                if not file_path.exists():
                    missing_files.append(filename)

            if missing_files:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing files in '{dir_name}': {missing_files}",
                )

            # Check that no unexpected files are in the directory
            try:
                actual_files = [f.name for f in dir_path.iterdir() if f.is_file()]
                unexpected_files = [f for f in actual_files if f not in expected_files and f not in SYSTEM_FILES]

                if unexpected_files:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Unexpected files in '{dir_name}': {unexpected_files}",
                    )
            except (OSError, PermissionError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error reading directory '{dir_name}': {e}",
                )

        return 1.0


@dataclass
class FileSizes(Evaluator["SizeClassificationTask", AgentRunResult]):
    """Evaluator that checks files are actually in the correct size categories."""

    async def evaluate(self, ctx: EvaluatorContext["SizeClassificationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are actually in the correct size categories."""
        task = ctx.inputs

        for dir_name in SIZE_RANGES:
            dir_path = task.work_dir / dir_name

            try:
                for file_path in dir_path.iterdir():
                    if file_path.is_file() and file_path.name not in SYSTEM_FILES:
                        file_size = file_path.stat().st_size

                        if dir_name == "small_files" and file_size >= MEDIUM_FILE_MIN:
                            msg = f"File {file_path.name} in small_files but size is {file_size} bytes"
                            return EvaluationReason(value=0.0, reason=msg)

                        if dir_name == "medium_files" and (file_size < MEDIUM_FILE_MIN or file_size > MEDIUM_FILE_MAX):
                            msg = f"File {file_path.name} in medium_files but size is {file_size} bytes"
                            return EvaluationReason(value=0.0, reason=msg)

                        if dir_name == "large_files" and file_size <= MEDIUM_FILE_MAX:
                            msg = f"File {file_path.name} in large_files but size is {file_size} bytes"
                            return EvaluationReason(value=0.0, reason=msg)
            except (OSError, PermissionError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error checking file sizes in '{dir_name}': {e}",
                )

        return 1.0


@dataclass
class TotalFileCount(Evaluator["SizeClassificationTask", AgentRunResult]):
    """Evaluator that checks all original files are accounted for."""

    async def evaluate(self, ctx: EvaluatorContext["SizeClassificationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all original files are accounted for."""
        task = ctx.inputs

        total_actual = 0
        for dir_name in REQUIRED_DIRS:
            dir_path = task.work_dir / dir_name
            if dir_path.exists():
                try:
                    files_in_dir = [f for f in dir_path.iterdir() if f.is_file() and f.name not in SYSTEM_FILES]
                    total_actual += len(files_in_dir)
                except (OSError, PermissionError):
                    continue

        if total_actual != TOTAL_EXPECTED_FILES:
            return EvaluationReason(
                value=0.0,
                reason=f"Expected {TOTAL_EXPECTED_FILES} files total, found {total_actual}",
            )

        return 1.0


class SizeClassificationTask(FilesystemTask):
    """Task for classifying files by size into three categories.

    The agent must:
    1. Create three directories: small_files/, medium_files/, large_files/
    2. Move files based on size: < 300 bytes, 300-700 bytes, > 700 bytes
    3. Ensure all files are classified correctly
    """

    name = "size_classification"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

Classify all files in the test directory into three categories based on their file size.
Create three subdirectories and move files accordingly.

### Task Objectives

1. **Create three directories** in the test directory:
   - `small_files/` - for files smaller than 300 bytes
   - `medium_files/` - for files between 300-700 bytes (inclusive)
   - `large_files/` - for files larger than 700 bytes

2. **Move all files** from the test directory into the appropriate subdirectory based on their size

3. **Handle all file types** - classify all files regardless of their extension (.txt, .jpg, .MOV, etc.)

### Expected Output

After completing the task, the directory structure should be:
- `small_files/` containing files < 300 bytes
- `medium_files/` containing files 300-700 bytes
- `large_files/` containing files > 700 bytes
- No files remain in the root test directory"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoriesExist(),
            FileClassification(),
            NoFilesInRoot(SYSTEM_FILES),
            FileSizes(),
            TotalFileCount(),
        )
