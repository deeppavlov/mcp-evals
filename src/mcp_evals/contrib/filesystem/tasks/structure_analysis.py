"""Structure Analysis task for filesystem domain."""

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FileReadable
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected values
EXPECTED_FILE_COUNT = 69
EXPECTED_FOLDER_COUNT = 51
EXPECTED_SIZE = 58097
SIZE_TOLERANCE = 1000
EXPECTED_DEPTH = 7
EXPECTED_TXT_COUNT = 68
EXPECTED_PY_COUNT = 1


@dataclass
class FileStatistics(Evaluator["StructureAnalysisTask", AgentRunResult]):
    """Evaluator that checks file statistics are correct."""

    async def evaluate(self, ctx: EvaluatorContext["StructureAnalysisTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify subtask 1: File Statistics."""
        task = ctx.inputs
        analysis_file = task.work_dir / "structure_analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")

            file_count_match = re.search(r"total number of files:\s*(\d+)", content, re.IGNORECASE)
            folder_count_match = re.search(r"total number of folders:\s*(\d+)", content, re.IGNORECASE)
            size_match = re.search(r"total size of all files:\s*(\d+)", content, re.IGNORECASE)

            if not file_count_match or not folder_count_match or not size_match:
                return EvaluationReason(
                    value=0.0,
                    reason="Could not extract file statistics from structure_analysis.txt",
                )

            file_count = int(file_count_match.group(1))
            folder_count = int(folder_count_match.group(1))
            total_size = int(size_match.group(1))

            if file_count != EXPECTED_FILE_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"File count must be {EXPECTED_FILE_COUNT}, found: {file_count}",
                )

            if folder_count != EXPECTED_FOLDER_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Folder count must be {EXPECTED_FOLDER_COUNT}, found: {folder_count}",
                )

            if abs(total_size - EXPECTED_SIZE) > SIZE_TOLERANCE:
                msg = f"Total size ({total_size}) is not within acceptable range ({EXPECTED_SIZE} ± {SIZE_TOLERANCE})"
                return EvaluationReason(value=0.0, reason=msg)

        except (OSError, UnicodeDecodeError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file statistics: {e}")

        return 1.0


@dataclass
class DepthAnalysis(Evaluator["StructureAnalysisTask", AgentRunResult]):
    """Evaluator that checks depth analysis is correct."""

    def _extract_depth(self, content: str) -> tuple[int | None, EvaluatorOutput | None]:
        """Extract depth from content."""
        depth_match = re.search(r"depth:\s*(\d+)", content, re.IGNORECASE)

        if not depth_match:
            return None, EvaluationReason(
                value=0.0,
                reason="Could not extract depth from structure_analysis.txt",
            )

        depth = int(depth_match.group(1))

        if depth != EXPECTED_DEPTH:
            return None, EvaluationReason(
                value=0.0,
                reason=f"Depth must be {EXPECTED_DEPTH}, found: {depth}",
            )

        return depth, None

    def _extract_and_validate_path(
        self, content: str, depth: int, task: "StructureAnalysisTask"
    ) -> tuple[str | None, EvaluatorOutput | None]:
        """Extract path and validate it."""
        lines = content.split("\n")
        path_line = None
        for i, line in enumerate(lines):
            if line.strip() == f"depth: {depth}" and i + 1 < len(lines):
                path_line = lines[i + 1].strip()
                break

        if not path_line:
            return None, EvaluationReason(
                value=0.0,
                reason="Could not find path line after depth specification",
            )

        # Verify that the path depth matches the declared depth
        path_parts = path_line.split("/")
        actual_depth = len(path_parts)

        if actual_depth != depth:
            msg = f"Path depth mismatch: declared depth is {depth}, but path has {actual_depth} levels"
            return None, EvaluationReason(value=0.0, reason=msg)

        # Verify that this path exists in the test environment
        expected_path = task.work_dir / path_line
        if not expected_path.exists():
            return None, EvaluationReason(value=0.0, reason=f"Path does not exist: {path_line}")

        if not expected_path.is_dir():
            return None, EvaluationReason(
                value=0.0,
                reason=f"Path exists but is not a directory: {path_line}",
            )

        return path_line, None

    async def evaluate(self, ctx: EvaluatorContext["StructureAnalysisTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify subtask 2: Depth Analysis."""
        task = ctx.inputs
        analysis_file = task.work_dir / "structure_analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")

            depth, error = self._extract_depth(content)
            if error is not None:
                return error
            if depth is None:
                return EvaluationReason(value=0.0, reason="Could not extract depth")

            _, error = self._extract_and_validate_path(content, depth, task)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying depth analysis: {e}")

        return 1.0


@dataclass
class FileTypeClassification(Evaluator["StructureAnalysisTask", AgentRunResult]):
    """Evaluator that checks file type classification is correct."""

    async def evaluate(self, ctx: EvaluatorContext["StructureAnalysisTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify subtask 3: File Type Classification."""
        task = ctx.inputs
        analysis_file = task.work_dir / "structure_analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")

            txt_match = re.search(r"txt:\s*(\d+)", content, re.IGNORECASE)
            py_match = re.search(r"py:\s*(\d+)", content, re.IGNORECASE)

            if not txt_match or not py_match:
                return EvaluationReason(
                    value=0.0,
                    reason="Could not extract file type counts from structure_analysis.txt",
                )

            txt_count = int(txt_match.group(1))
            py_count = int(py_match.group(1))

            if txt_count != EXPECTED_TXT_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"txt count must be {EXPECTED_TXT_COUNT}, found: {txt_count}",
                )

            if py_count != EXPECTED_PY_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"py count must be {EXPECTED_PY_COUNT}, found: {py_count}",
                )

        except (OSError, UnicodeDecodeError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file type classification: {e}")

        return 1.0


@dataclass
class FileFormat(Evaluator["StructureAnalysisTask", AgentRunResult]):
    """Evaluator that checks structure_analysis.txt file has proper format."""

    async def evaluate(self, ctx: EvaluatorContext["StructureAnalysisTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the structure_analysis.txt file has proper format."""
        task = ctx.inputs
        analysis_file = task.work_dir / "structure_analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            if len(lines) < 5:  # noqa: PLR2004
                return EvaluationReason(
                    value=0.0,
                    reason="File seems too short to contain all required information",
                )

            if not content.strip():
                return EvaluationReason(value=0.0, reason="File is completely empty")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file format: {e}")

        return 1.0


class StructureAnalysisTask(FilesystemTask):
    """Task for analyzing directory structure and generating statistical report.

    The agent must:
    1. Count total files, folders, and total size
    2. Identify deepest folder path and calculate depth
    3. Classify files by extension and count each type
    """

    name = "structure_analysis"
    goal = """Please use FileSystem tools to finish the following task:

You need to recursively traverse the entire folder structure under the main directory and generate a \
detailed statistical report in a file named `structure_analysis.txt`.

**Important**:
- In all tasks, ignore `.DS_Store` files (except for subtask 1 total size calculation).
- You should not change or delete any existed files.
- Do not try to use python code.

---

### 1. File Statistics

Count the following information for the entire directory structure:
- total number of files (exclude .DS_Store)
- total number of folders
- total size of all files (in bytes, include .DS_Store only in this subtask)

**Format (one item per line):**
total number of files: X
total number of folders: Y
total size of all files: Z

---

### 2. Depth Analysis

Identify the deepest folder path(s) in the directory and calculate its depth level.
- Use relative paths based on main directory.
- **Write the folder path only up to the folder, not including the file name. For example, if the file path \
is `./complex_structure/A/B/C/def.txt`, then the path in your report should be `complex_structure/A/B/C`, \
and the depth is `4`.**
- If multiple deepest paths exist, list only one.

**Format (one item per line):**
depth: N
PATH

---

### 3. File Type Classification

Categorize files by their extensions and count the number of files for each type. Files without extensions \
should also be included.

**Format (one extension per line):**
txt: count
py: count
jpg: count
mov: count
(no extension): count"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("structure_analysis.txt"),
            FileReadable("structure_analysis.txt"),
            FileStatistics(),
            DepthAnalysis(),
            FileTypeClassification(),
            FileFormat(),
        )
