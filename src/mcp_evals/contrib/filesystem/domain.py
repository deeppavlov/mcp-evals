"""Filesystem domain for MCP Universe filesystem evaluations."""

from collections.abc import Sequence
from contextlib import AsyncExitStack
from pathlib import Path

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
    DatasetComparisonTask,
    DebuggingTask,
    DisputeReviewTask,
    DuplicateNameTask,
    DuplicatesSearchingTask,
    EnglishTalentTask,
    FileArrangementTask,
    FileMergingTask,
    FileSplittingTask,
    FindMathPaperTask,
    GradebasedScoreTask,
    IndividualCommentsTask,
    MusicReportTask,
    OrganizeLegacyPapersTask,
    OutputAnalysisTask,
    PatternMatchingTask,
    ProjectManagementTask,
    RequirementsCompletionTask,
    RequirementsWritingTask,
    SizeClassificationTask,
    SolutionTracingTask,
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
    _stack: AsyncExitStack | None = None

    async def setup(self) -> None:
        """Create tmp dir for filesystem operations."""
        if self._stack is not None:
            msg = "Attempted to create FilesystemDomain again"
            raise RuntimeError(msg)

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        logger.debug(f"[{self.name}] Creating workspace directory...")
        tmpdir_ctx = aiofiles.tempfile.TemporaryDirectory(prefix="mcp-filesystem-")
        self._tmp_dir = Path(await self._stack.enter_async_context(tmpdir_ctx))

    async def teardown(self) -> None:  # noqa: D102
        if self._stack is None:
            msg = "FilesystemDomain wasn't created"
            logger.exception(msg)
            raise RuntimeError(msg)

        await self._stack.aclose()

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
                    "mcp/filesystem",
                    "/projects",
                ],
            )
        ]

    def tasks(self) -> Sequence[FilesystemTask]:
        """Return all filesystem tasks."""
        return [
            MusicReportTask(self._tmp_dir, fixture=Fixture.DESKTOP),
            ProjectManagementTask(self._tmp_dir, fixture=Fixture.DESKTOP),
            TimelineExtractionTask(self._tmp_dir, fixture=Fixture.DESKTOP),
            BudgetComputationTask(self._tmp_dir, fixture=Fixture.DESKTOP_TEMPLATE),
            ContactInformationTask(self._tmp_dir, fixture=Fixture.DESKTOP_TEMPLATE),
            FileArrangementTask(self._tmp_dir, fixture=Fixture.DESKTOP_TEMPLATE),
            SizeClassificationTask(self._tmp_dir, fixture=Fixture.FILE_PROPERTY),
            TimeClassificationTask(self._tmp_dir, fixture=Fixture.FILE_PROPERTY),
            StructureAnalysisTask(self._tmp_dir, fixture=Fixture.FOLDER_STRUCTURE),
            StructureMirrorTask(self._tmp_dir, fixture=Fixture.FOLDER_STRUCTURE),
            DisputeReviewTask(self._tmp_dir, fixture=Fixture.LEGAL_DOCUMENT),
            IndividualCommentsTask(self._tmp_dir, fixture=Fixture.LEGAL_DOCUMENT),
            SolutionTracingTask(self._tmp_dir, fixture=Fixture.LEGAL_DOCUMENT),
            AuthorFoldersTask(self._tmp_dir, fixture=Fixture.PAPERS),
            FindMathPaperTask(self._tmp_dir, fixture=Fixture.PAPERS),
            OrganizeLegacyPapersTask(self._tmp_dir, fixture=Fixture.PAPERS),
            DuplicateNameTask(self._tmp_dir, fixture=Fixture.STUDENT_DATABASE),
            EnglishTalentTask(self._tmp_dir, fixture=Fixture.STUDENT_DATABASE),
            GradebasedScoreTask(self._tmp_dir, fixture=Fixture.STUDENT_DATABASE),
            CodeLocatingTask(self._tmp_dir, fixture=Fixture.THREESTUDIO),
            OutputAnalysisTask(self._tmp_dir, fixture=Fixture.THREESTUDIO),
            RequirementsCompletionTask(self._tmp_dir, fixture=Fixture.THREESTUDIO),
            DatasetComparisonTask(self._tmp_dir, fixture=Fixture.VOTENET),
            DebuggingTask(self._tmp_dir, fixture=Fixture.VOTENET),
            RequirementsWritingTask(self._tmp_dir, fixture=Fixture.VOTENET),
            DuplicatesSearchingTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT),
            FileMergingTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT),
            FileSplittingTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT),
            PatternMatchingTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT),
            UppercaseTask(self._tmp_dir, fixture=Fixture.FILE_CONTEXT),
        ]
