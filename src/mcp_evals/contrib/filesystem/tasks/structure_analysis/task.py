"""Structure Analysis task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileContentStructure, FileExists, FileReadable
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.tasks.structure_analysis.custom_evaluators import (
    DepthAnalysis,
    FileStatistics,
    FileTypeClassification,
)
from mcp_evals.contrib.filesystem.utils import Fixture


class StructureAnalysisTask(FilesystemTask):
    """Task for analyzing directory structure and generating statistical report.

    The agent must:
    1. Count total files, folders, and total size
    2. Identify deepest folder path and calculate depth
    3. Classify files by extension and count each type
    """

    name = "structure_analysis"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("structure_analysis.txt"),
            FileReadable("structure_analysis.txt"),
            FileContentStructure("structure_analysis.txt", min_lines=5),
            FileStatistics(),
            DepthAnalysis(),
            FileTypeClassification(),
        )
