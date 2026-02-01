"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.task import Task


@dataclass
class DirectoryExists(Evaluator[Task, AgentRunResult]):
    """Evaluator that checks if a directory exists.

    Example:
        DirectoryExists("duplicates")
        DirectoryExists("music/reports")
    """

    path: str

    async def evaluate(self, ctx: EvaluatorContext[Task, AgentRunResult]) -> EvaluatorOutput:
        """Check if the directory at the specified path exists.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs
        if not hasattr(task, "work_dir") or task.work_dir is None:
            return EvaluationReason(
                value=0.0,
                reason="Task work_dir not set",
            )

        dir_path = task.work_dir / self.path

        if dir_path.exists() and dir_path.is_dir():
            return 1.0
        return EvaluationReason(
            value=0.0,
            reason=f"Directory '{self.path}' does not exist or is not a directory",
        )


@dataclass
class FileCount(Evaluator[Task, AgentRunResult]):
    """Evaluator that checks if a directory contains the expected number of files.

    Example:
        FileCount("duplicates", expected=14)
        FileCount("music", expected=20)
    """

    path: str
    expected: int

    async def evaluate(self, ctx: EvaluatorContext[Task, AgentRunResult]) -> EvaluatorOutput:
        """Check if the directory contains the expected number of files.

        The path is resolved relative to the task's work directory.
        Only counts files, not subdirectories.
        """
        task = ctx.inputs
        if not hasattr(task, "work_dir") or task.work_dir is None:
            return EvaluationReason(
                value=0.0,
                reason="Task work_dir not set",
            )

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
class FileContentStructure(Evaluator[Task, AgentRunResult]):
    """Evaluator that checks file content structure (line count, format).

    Example:
        FileContentStructure("report.txt", expected_lines=25)
        FileContentStructure("data.csv", expected_lines=100, min_lines=50)
    """

    path: str
    expected_lines: int | None = None
    min_lines: int | None = None
    max_lines: int | None = None

    async def evaluate(self, ctx: EvaluatorContext[Task, AgentRunResult]) -> EvaluatorOutput:  # noqa: PLR0911
        """Check if the file has the expected line count.

        The path is resolved relative to the task's work directory.
        """
        task = ctx.inputs
        if not hasattr(task, "work_dir") or task.work_dir is None:
            return EvaluationReason(
                value=0.0,
                reason="Task work_dir not set",
            )

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
