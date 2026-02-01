"""Built-in evaluators for common evaluation scenarios."""

import re
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.task import Task


class FileExists(Evaluator[Task, AgentRunResult]):
    """Evaluator that checks if a file exists.

    Example:
    - `FileExists("config.json")`
    - `FileExists("music/music_analysis_report.txt")`
    """

    path: str

    async def evaluate(self, _ctx: EvaluatorContext[Task, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file at the specified path exists.

        The path is resolved relative to the current working directory
        or the filesystem root if set via environment variable.
        """
        file_path = Path(self.path)

        if file_path.exists() and file_path.is_file():
            return EvaluatorOutput(value=1.0)
        return EvaluationReason(
            value=0.0,
            reason=f"File '{self.path}' does not exist or is not a file",
        )


class ContentMatches(Evaluator[Task, AgentRunResult]):
    r"""Evaluator that checks if file content matches a regex pattern.

    Example:
    - `ContentMatches("config.json", pattern=r'"port":\s*8080')`
    - `ContentMatches("music/music_analysis_report.txt", pattern=r"晴天.*2\.576")`
    """

    path: str
    pattern: str

    async def evaluate(self, _ctx: EvaluatorContext[Task, AgentRunResult]) -> EvaluatorOutput:
        """Check if the file content matches the specified regex pattern.

        The file is read as text and searched for the pattern.
        """
        file_path = Path(self.path)

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
            if re.search(self.pattern, content):
                return EvaluatorOutput(value=1.0)
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.path}' content does not match pattern '{self.pattern}'",
            )
        except PermissionError as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading file '{self.path}': {e}",
            )
