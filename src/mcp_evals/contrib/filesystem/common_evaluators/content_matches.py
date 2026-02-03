"""Common evaluators shared across filesystem tasks."""

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


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
