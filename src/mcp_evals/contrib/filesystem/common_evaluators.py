"""Common evaluators shared across filesystem tasks."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from .task import FilesystemTask


@dataclass
class FileExists(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a file exists.

    Example:
    - `FileExists("config.json")`
    - `FileExists("music/music_analysis_report.txt")`
    """

    path: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file at the specified path exists.

        The path is resolved relative to the current working directory
        or the filesystem root if set via environment variable.
        """
        task = ctx.inputs
        file_path = task.work_dir / Path(self.path)

        if file_path.exists() and file_path.is_file():
            return 1.0
        return EvaluationReason(
            value=0.0,
            reason=f"File '{self.path}' does not exist or is not a file",
        )


@dataclass
class ContentMatches(Evaluator[FilesystemTask, AgentRunResult]):
    r"""Evaluator that checks if file content matches a regex pattern.

    Example:
    - `ContentMatches("config.json", pattern=r'"port":\s*8080')`
    - `ContentMatches("music/music_analysis_report.txt", pattern=r"晴天.*2\.576")`
    """

    path: str
    pattern: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file content matches the specified regex pattern.

        The file is read as text and searched for the pattern.
        """
        task = ctx.inputs
        file_path = task.work_dir / Path(self.path)

        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' does not exist",
            )

        if not file_path.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.path}' is not a file",
            )

        try:
            content = file_path.read_text(encoding="utf-8")
            if re.search(self.pattern, content, re.DOTALL):
                return 1.0
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' content does not match pattern '{self.pattern}'",
            )
        except PermissionError as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading file '{self.path}': {e}",
            )


@dataclass
class DirectoryExists(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a directory exists.

    Example:
        DirectoryExists("duplicates")
        DirectoryExists("music/reports")
    """

    path: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the directory at the specified path exists.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs

        dir_path = task.work_dir / self.path

        if dir_path.exists() and dir_path.is_dir():
            return 1.0
        return EvaluationReason(
            value=0.0,
            reason=f"Directory '{self.path}' does not exist or is not a directory",
        )


@dataclass
class FileCount(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a directory contains the expected number of files.

    Example:
        FileCount("duplicates", expected=14)
        FileCount("music", expected=20)
    """

    path: str
    expected: int

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the directory contains the expected number of files.

        The path is resolved relative to the task's work directory.
        Only counts files, not subdirectories.
        """
        task = ctx.inputs

        dir_path = task.work_dir / self.path

        if not dir_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"Directory '{self.path}' does not exist",
            )

        if not dir_path.is_dir():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.path}' is not a directory",
            )

        try:
            file_count = sum(1 for item in dir_path.iterdir() if item.is_file())
            if file_count == self.expected:
                return 1.0
            return EvaluationReason(
                value=0.0,
                reason=f"Directory '{self.path}' contains {file_count} files, expected {self.expected}",
            )
        except PermissionError as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading directory '{self.path}': {e}",
            )


@dataclass
class FileContentStructure(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks file content structure (line count, format).

    Example:
        FileContentStructure("report.txt", expected_lines=25)
        FileContentStructure("data.csv", expected_lines=100, min_lines=50)
    """

    path: str
    expected_lines: int | None = None
    min_lines: int | None = None
    max_lines: int | None = None

    def _validate_file_path(self, file_path: Path) -> EvaluatorOutput | None:
        """Validate that the file path exists and is a file."""
        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' does not exist",
            )
        if not file_path.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.path}' is not a file",
            )
        return None

    def _validate_line_count(self, line_count: int) -> EvaluatorOutput | None:
        """Validate line count against expected, min, and max constraints."""
        if self.expected_lines is not None and line_count != self.expected_lines:
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' has {line_count} lines, expected {self.expected_lines}",
            )
        if self.min_lines is not None and line_count < self.min_lines:
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' has {line_count} lines, expected at least {self.min_lines}",
            )
        if self.max_lines is not None and line_count > self.max_lines:
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' has {line_count} lines, expected at most {self.max_lines}",
            )
        return None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file has the expected line count.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs
        file_path = task.work_dir / self.path

        validation_error = self._validate_file_path(file_path)
        if validation_error is not None:
            return validation_error

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            line_count = len(lines)
        except PermissionError as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading file '{self.path}': {e}",
            )
        except UnicodeDecodeError as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error decoding file '{self.path}': {e}",
            )

        line_count_error = self._validate_line_count(line_count)
        if line_count_error is not None:
            return line_count_error

        return 1.0


@dataclass
class FileReadable(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if a file exists and is readable/not empty.

    Example:
    - `FileReadable("timeline.txt")`
    - `FileReadable("structure_analysis.txt")`
    """

    path: str

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file at the specified path exists and is readable/not empty.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs
        file_path = task.work_dir / Path(self.path)

        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' does not exist",
            )

        if not file_path.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.path}' is not a file",
            )

        try:
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                return EvaluationReason(
                    value=0.0,
                    reason=f"File '{self.path}' is empty",
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading file '{self.path}': {e}",
            )

        return 1.0


@dataclass
class NoFilesInRoot(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks no files remain in the root directory.

    Example:
    - `NoFilesInRoot()`
    - `NoFilesInRoot([".DS_Store", "Thumbs.db"])`
    """

    system_files: list[str] | None = None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check that no files remain in the root directory.

        Optionally ignores system files like .DS_Store, Thumbs.db, etc.
        """
        task = ctx.inputs

        if self.system_files is None:
            system_files = [".DS_Store", "Thumbs.db", ".DS_Store?", "._.DS_Store"]
        else:
            system_files = self.system_files

        try:
            root_files = [f for f in task.work_dir.iterdir() if f.is_file()]
            non_system_files = [f for f in root_files if f.name not in system_files]

            if non_system_files:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Files still present in root directory: {[f.name for f in non_system_files]}",
                )
        except (OSError, PermissionError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading root directory: {e}",
            )

        return 1.0


@dataclass
class CSVFormat(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks CSV file has correct structure.

    Example:
    - `CSVFormat("individual_comment.csv", expected_columns=7)`
    - `CSVFormat("tracing.csv", expected_columns=5, min_rows=10)`
    """

    path: str
    expected_columns: int
    min_rows: int = 2

    def _validate_file_path(self, file_path: Path) -> EvaluatorOutput | None:
        """Validate that the file path exists and is a file."""
        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"CSV file '{self.path}' does not exist",
            )
        if not file_path.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"Path '{self.path}' is not a file",
            )
        return None

    def _validate_csv_structure(self, rows: list[list[str]]) -> EvaluatorOutput | None:
        """Validate CSV structure: row count, header, and data rows."""
        if not rows:
            return EvaluationReason(
                value=0.0,
                reason=f"CSV file '{self.path}' is empty",
            )

        if len(rows) < self.min_rows:
            return EvaluationReason(
                value=0.0,
                reason=(
                    f"CSV file '{self.path}' has insufficient rows: {len(rows)}, expected at least {self.min_rows}"
                ),
            )

        header = rows[0]
        if len(header) != self.expected_columns:
            return EvaluationReason(
                value=0.0,
                reason=(
                    f"Header row in '{self.path}' has incorrect number of columns: "
                    f"{len(header)}, expected {self.expected_columns}"
                ),
            )

        for i, row in enumerate(rows[1:], 1):
            if len(row) != self.expected_columns:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Data row {i} in '{self.path}' has incorrect number of columns: "
                        f"{len(row)}, expected {self.expected_columns}"
                    ),
                )

        return None

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Check if the CSV file has the correct format.

        Verifies:
        - File exists and is readable
        - Has at least min_rows rows (default 2: header + at least 1 data row)
        - Header row has expected_columns columns
        - All data rows have expected_columns columns
        """
        task = ctx.inputs
        file_path = task.work_dir / Path(self.path)

        validation_error = self._validate_file_path(file_path)
        if validation_error is not None:
            return validation_error

        try:
            with file_path.open("r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                structure_error = self._validate_csv_structure(rows)
                if structure_error is not None:
                    return structure_error

                return 1.0
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading CSV file '{self.path}': {e}",
            )
