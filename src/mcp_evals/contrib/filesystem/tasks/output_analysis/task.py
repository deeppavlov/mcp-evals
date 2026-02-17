"""Output Analysis task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import FilePath, LineNumbers, RequiredStrings


class OutputAnalysisTask(FilesystemTask):
    """Task for analyzing Zero123 guidance output structure.

    The agent must:
    1. Find the output of guidance_out at line 137 in threestudio/systems/zero123.py
    2. State the structure and where it's found (file and line numbers)
    3. Create answer.txt with four required fields: loss_sds, grad_norm, min_step, max_step
    4. Include line numbers (323-324 and 327-328) and file path
    """

    name = "output_analysis"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("answer.txt"),
            RequiredStrings(),
            LineNumbers(),
            FilePath(),
        )
