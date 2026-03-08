"""Filesystem domain for MCP Universe filesystem evaluations."""

from collections.abc import Sequence
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import aiofiles
from loguru import logger
from pydantic_ai.mcp import MCPServerStdio

from mcp_evals import Domain
from mcp_evals.contrib.filesystem.utils import Fixture
from mcp_evals.secrets import DomainSecrets

from .task import FilesystemTask
from .tasks import (
    AuthorFoldersTask,
    BudgetComputationTask,
    CodeLocatingTask,
    ContactInformationTask,
    DatasetComparisonTask,  # noqa: F401
    DebuggingTask,
    DisputeReviewTask,  # noqa: F401
    DuplicateNameTask,
    DuplicatesSearchingTask,
    EnglishTalentTask,
    FileArrangementTask,
    FileMergingTask,
    FileSplittingTask,  # noqa: F401
    FindMathPaperTask,
    GradebasedScoreTask,
    IndividualCommentsTask,  # noqa: F401
    MusicReportTask,
    OrganizeLegacyPapersTask,
    OutputAnalysisTask,
    PatternMatchingTask,
    ProjectManagementTask,
    RequirementsCompletionTask,
    RequirementsWritingTask,
    SizeClassificationTask,
    SolutionTracingTask,  # noqa: F401
    StructureAnalysisTask,
    StructureMirrorTask,
    TimeClassificationTask,
    TimelineExtractionTask,
    UppercaseTask,
)


class FilesystemDomain(Domain[DomainSecrets]):
    """Domain for filesystem tasks from MCP Universe.

    Provides MCP filesystem server and groups related filesystem tasks.
    """

    name = "filesystem"

    def __init__(self, tool_retries: int = 1) -> None:
        """Init."""
        super().__init__(tool_retries=tool_retries)

    async def setup(self, stack: AsyncExitStack[Any]) -> None:
        """Create tmp dir for filesystem operations."""
        logger.debug(f"[{self.name}] Creating workspace directory...")
        tmpdir_ctx = aiofiles.tempfile.TemporaryDirectory(prefix="mcp-filesystem-")
        self._tmp_dir = Path(await stack.enter_async_context(tmpdir_ctx))

    def mcp_servers(self) -> Sequence[MCPServerStdio]:
        """Return MCP filesystem server configuration."""
        return [
            MCPServerStdio(
                "docker",
                [
                    "run",
                    "-i",
                    "--rm",
                    "--mount",
                    f"type=bind,src={self._tmp_dir},dst=/projects",
                    "-w",
                    "/projects",
                    "mcp-filesystem-server:mcp-evals",
                    "/projects",
                ],
                max_retries=self.tool_retries,
            )
        ]

    def _tasks_impl(self) -> Sequence[FilesystemTask]:
        """Return all filesystem tasks."""
        return [
            MusicReportTask(self._tmp_dir, fixture=Fixture.DESKTOP, tool_retries=self.tool_retries),
            ProjectManagementTask(self._tmp_dir, fixture=Fixture.DESKTOP, tool_retries=self.tool_retries),
            TimelineExtractionTask(self._tmp_dir, fixture=Fixture.DESKTOP, tool_retries=self.tool_retries),
            BudgetComputationTask(self._tmp_dir, fixture=Fixture.DESKTOP_TEMPLATE, tool_retries=self.tool_retries),
            ContactInformationTask(self._tmp_dir, fixture=Fixture.DESKTOP_TEMPLATE, tool_retries=self.tool_retries),
            FileArrangementTask(self._tmp_dir, fixture=Fixture.DESKTOP_TEMPLATE, tool_retries=self.tool_retries),
            SizeClassificationTask(self._tmp_dir, fixture=Fixture.FILE_PROPERTY, tool_retries=self.tool_retries),
            TimeClassificationTask(self._tmp_dir, fixture=Fixture.FILE_PROPERTY, tool_retries=self.tool_retries),
            StructureAnalysisTask(self._tmp_dir, fixture=Fixture.FOLDER_STRUCTURE, tool_retries=self.tool_retries),
            StructureMirrorTask(self._tmp_dir, fixture=Fixture.FOLDER_STRUCTURE, tool_retries=self.tool_retries),
            # DisputeReviewTask(self._tmp_dir, fixture=Fixture.LEGAL_DOCUMENT, tool_retries=self.tool_retries),
            # IndividualCommentsTask(self._tmp_dir, fixture=Fixture.LEGAL_DOCUMENT, tool_retries=self.tool_retries),
            # SolutionTracingTask(self._tmp_dir, fixture=Fixture.LEGAL_DOCUMENT, tool_retries=self.tool_retries),
            AuthorFoldersTask(self._tmp_dir, fixture=Fixture.PAPERS, tool_retries=self.tool_retries),
            FindMathPaperTask(self._tmp_dir, fixture=Fixture.PAPERS, tool_retries=self.tool_retries),
            OrganizeLegacyPapersTask(self._tmp_dir, fixture=Fixture.PAPERS, tool_retries=self.tool_retries),
            DuplicateNameTask(self._tmp_dir, fixture=Fixture.STUDENT_DATABASE, tool_retries=self.tool_retries),
            EnglishTalentTask(self._tmp_dir, fixture=Fixture.STUDENT_DATABASE, tool_retries=self.tool_retries),
            GradebasedScoreTask(self._tmp_dir, fixture=Fixture.STUDENT_DATABASE, tool_retries=self.tool_retries),
            CodeLocatingTask(self._tmp_dir, fixture=Fixture.THREESTUDIO, tool_retries=self.tool_retries),
            OutputAnalysisTask(self._tmp_dir, fixture=Fixture.THREESTUDIO, tool_retries=self.tool_retries),
            RequirementsCompletionTask(self._tmp_dir, fixture=Fixture.THREESTUDIO, tool_retries=self.tool_retries),
            # DatasetComparisonTask(self._tmp_dir, fixture=Fixture.VOTENET, tool_retries=self.tool_retries),
            DebuggingTask(self._tmp_dir, fixture=Fixture.VOTENET, tool_retries=self.tool_retries),
            RequirementsWritingTask(self._tmp_dir, fixture=Fixture.VOTENET, tool_retries=self.tool_retries),
            DuplicatesSearchingTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT, tool_retries=self.tool_retries),
            FileMergingTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT, tool_retries=self.tool_retries),
            # FileSplittingTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT, tool_retries=self.tool_retries),
            PatternMatchingTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT, tool_retries=self.tool_retries),
            UppercaseTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT, tool_retries=self.tool_retries),
        ]
