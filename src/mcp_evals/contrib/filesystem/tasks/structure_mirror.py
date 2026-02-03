"""Structure Mirror task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected directories that should exist
EXPECTED_DIRS = [
    "deeply",
    "deeply/nested",
    "deeply/nested/folder",
    "deeply/nested/folder/structure",
    "empty_folder",
    "folder_lxkHt_0_1_processed",
    "folder_QdTAj_0_2_processed",
    "folder_xtgyi_0_0_processed",
    "mixed_content",
    "mixed_content/images_and_text",
    "project",
    "project/docs",
    "project/docs/archive",
    "project/docs/archive/2023_processed",
    "project/src",
    "project/src/main",
    "project/src/main/resources",
]

# Directories that should have placeholder.txt files
PLACEHOLDER_DIRS = [
    "deeply/nested/folder/structure",
    "empty_folder",
    "folder_lxkHt_0_1_processed",
    "folder_QdTAj_0_2_processed",
    "folder_xtgyi_0_0_processed",
    "mixed_content/images_and_text",
    "project/docs/archive/2023_processed",
    "project/src/main/resources",
]

MIRROR_DIR_NAME = "complex_structure_mirror"
SOURCE_DIR_NAME = "complex_structure"


def find_mirror_directory(work_dir: Path) -> Path | None:
    """Find the mirror directory."""
    mirror_dir = work_dir / MIRROR_DIR_NAME
    if mirror_dir.exists() and mirror_dir.is_dir():
        return mirror_dir
    return None


@dataclass
class MirrorDirectoryExists(Evaluator["StructureMirrorTask", AgentRunResult]):
    """Evaluator that checks mirror directory exists."""

    async def evaluate(self, ctx: EvaluatorContext["StructureMirrorTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the mirror directory exists."""
        task = ctx.inputs
        mirror_dir = find_mirror_directory(task.work_dir)

        if mirror_dir is None:
            return EvaluationReason(
                value=0.0,
                reason=f"Mirror directory '{MIRROR_DIR_NAME}' not found",
            )

        return 1.0


@dataclass
class NoFilesCopied(Evaluator["StructureMirrorTask", AgentRunResult]):
    """Evaluator that checks no file contents were copied, only directory structure."""

    async def evaluate(self, ctx: EvaluatorContext["StructureMirrorTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that no file contents were copied, only directory structure."""
        task = ctx.inputs
        source_dir = task.work_dir / SOURCE_DIR_NAME
        mirror_dir = find_mirror_directory(task.work_dir)

        if mirror_dir is None:
            return EvaluationReason(value=0.0, reason=f"Mirror directory '{MIRROR_DIR_NAME}' not found")

        if not source_dir.exists():
            return EvaluationReason(value=0.0, reason=f"Source directory '{SOURCE_DIR_NAME}' not found")

        try:
            # Check that no files from source were copied (except placeholder.txt files)
            for source_file in source_dir.rglob("*"):
                if source_file.is_file():
                    relative_path = source_file.relative_to(source_dir)
                    mirror_file = mirror_dir / relative_path

                    # Skip if this would be a placeholder.txt file
                    if mirror_file.name == "placeholder.txt":
                        continue

                    if mirror_file.exists():
                        return EvaluationReason(
                            value=0.0,
                            reason=f"File was copied when it shouldn't be: {relative_path}",
                        )
        except (OSError, PermissionError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking copied files: {e}")

        return 1.0


@dataclass
class MirrorStructureCompleteness(Evaluator["StructureMirrorTask", AgentRunResult]):
    """Evaluator that checks mirror structure is complete and matches expected structure."""

    def _check_directory_exists(self, mirror_path: Path, expected_dir: str) -> EvaluatorOutput | None:
        """Check that a directory exists and is actually a directory."""
        if not mirror_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"Expected directory not found: {expected_dir}",
            )

        if not mirror_path.is_dir():
            return EvaluationReason(
                value=0.0,
                reason=f"Expected directory exists but is not a directory: {expected_dir}",
            )
        return None

    def _check_placeholder_file(
        self, placeholder_file: Path, expected_dir: str, mirror_dir: Path
    ) -> EvaluatorOutput | None:
        """Check placeholder.txt file exists and has correct content."""
        if not placeholder_file.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"placeholder.txt not found in: {expected_dir}",
            )

        if not placeholder_file.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"placeholder.txt exists but is not a file in: {expected_dir}",
            )

        try:
            content = placeholder_file.read_text(encoding="utf-8").strip()

            if not content:
                return EvaluationReason(
                    value=0.0,
                    reason=f"placeholder.txt is empty in: {expected_dir}",
                )

            rel_mirror = placeholder_file.parent.relative_to(mirror_dir)
            expected_ending = f"{MIRROR_DIR_NAME}/{rel_mirror}"

            if not content.endswith(expected_ending):
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"placeholder.txt content incorrect in: {expected_dir}. "
                        f"Expected ending: {expected_ending}, Found: {content}"
                    ),
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading placeholder.txt in {expected_dir}: {e}",
            )
        return None

    def _check_unexpected_directories(self, mirror_dir: Path) -> EvaluatorOutput | None:
        """Check that no unexpected directories exist."""
        try:
            for mirror_subdir in mirror_dir.rglob("*"):
                if mirror_subdir.is_dir():
                    relative_path = mirror_subdir.relative_to(mirror_dir)
                    if str(relative_path) not in EXPECTED_DIRS and str(relative_path) != ".":
                        return EvaluationReason(
                            value=0.0,
                            reason=f"Unexpected directory found: {relative_path}",
                        )
        except (OSError, PermissionError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking directory structure: {e}")
        return None

    async def evaluate(self, ctx: EvaluatorContext["StructureMirrorTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the mirror structure is complete and matches expected structure."""
        task = ctx.inputs
        mirror_dir = find_mirror_directory(task.work_dir)

        if mirror_dir is None:
            return EvaluationReason(value=0.0, reason=f"Mirror directory '{MIRROR_DIR_NAME}' not found")

        # Check that all expected directories exist
        for expected_dir in EXPECTED_DIRS:
            mirror_path = mirror_dir / expected_dir

            dir_check = self._check_directory_exists(mirror_path, expected_dir)
            if dir_check is not None:
                return dir_check

            if expected_dir in PLACEHOLDER_DIRS:
                placeholder_file = mirror_path / "placeholder.txt"
                placeholder_check = self._check_placeholder_file(placeholder_file, expected_dir, mirror_dir)
                if placeholder_check is not None:
                    return placeholder_check

        # Check that no unexpected directories exist
        unexpected_check = self._check_unexpected_directories(mirror_dir)
        if unexpected_check is not None:
            return unexpected_check

        return 1.0


class StructureMirrorTask(FilesystemTask):
    """Task for mirroring directory structure with smart placeholders.

    The agent must:
    1. Copy entire directory structure of complex_structure/ to complex_structure_mirror/
    2. Do not copy any file contents, only create directories
    3. In each empty directory, create placeholder.txt with absolute path
    4. Discard directories that directly contain more than 2 files
    5. If directory name contains numbers, append "_processed" to mirror directory name
    """

    name = "structure_mirror"
    goal = """Please use FileSystem tools to finish the following task:

### Task

Copy the entire directory structure of `complex_structure/` to `complex_structure_mirror/`
without copying any file contents. Do not use python code.

### Requirements

- Create the entire directory structure in `complex_structure_mirror/`
- Do not copy any file contents, only create directories
- In each empty directory, create a `placeholder.txt` file containing the absolute path of that directory
- Handle nested directories of any depth
- You should also follow 2 rules:
  1. **Discard any directory that directly contains more than 2 files (only count the immediate folder).**
  2. **If a directory name contains numbers, append "_processed" to the mirror directory name**

### Expected Output

After completing the task:
- `complex_structure_mirror/` directory exists
- All directories from `complex_structure/` are mirrored with modified names (if they contain numbers)
- Directories with more than 2 files are excluded
- Each empty directory contains a `placeholder.txt` file with the absolute path
- No file contents from the source directory are copied"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists(MIRROR_DIR_NAME),
            NoFilesCopied(),
            MirrorStructureCompleteness(),
        )
