"""Common evaluators shared across filesystem tasks."""

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

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:  # noqa: PLR0911
        """Check if the file has the expected line count.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs

        file_path = task.work_dir / self.path

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
            lines = content.strip().split("\n")
            line_count = len(lines)

            # Check exact line count if specified
            if self.expected_lines is not None and line_count != self.expected_lines:
                return EvaluationReason(
                    value=0.0,
                    reason=f"File '{self.path}' has {line_count} lines, expected {self.expected_lines}",
                )

            # Check min lines if specified
            if self.min_lines is not None and line_count < self.min_lines:
                return EvaluationReason(
                    value=0.0,
                    reason=f"File '{self.path}' has {line_count} lines, expected at least {self.min_lines}",
                )

            # Check max lines if specified
            if self.max_lines is not None and line_count > self.max_lines:
                return EvaluationReason(
                    value=0.0,
                    reason=f"File '{self.path}' has {line_count} lines, expected at most {self.max_lines}",
                )

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
        else:
            return 1.0
