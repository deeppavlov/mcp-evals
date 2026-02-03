"""Filesystem tasks for MCP Universe evaluations."""

from .author_folders.task import AuthorFoldersTask
from .budget_computation.task import BudgetComputationTask
from .code_locating.task import CodeLocatingTask
from .contact_information.task import ContactInformationTask
from .dataset_comparison.task import DatasetComparisonTask
from .debugging.task import DebuggingTask
from .dispute_review.task import DisputeReviewTask
from .duplicate_name.task import DuplicateNameTask
from .duplicates_searching.task import DuplicatesSearchingTask
from .english_talent.task import EnglishTalentTask
from .file_arrangement.task import FileArrangementTask
from .file_merging.task import FileMergingTask
from .file_splitting.task import FileSplittingTask
from .find_math_paper.task import FindMathPaperTask
from .gradebased_score.task import GradebasedScoreTask
from .individual_comments.task import IndividualCommentsTask
from .music_report.task import MusicReportTask
from .organize_legacy_papers.task import OrganizeLegacyPapersTask
from .output_analysis.task import OutputAnalysisTask
from .pattern_matching.task import PatternMatchingTask
from .project_management.task import ProjectManagementTask
from .requirements_completion.task import RequirementsCompletionTask
from .requirements_writing.task import RequirementsWritingTask
from .size_classification.task import SizeClassificationTask
from .solution_tracing.task import SolutionTracingTask
from .structure_analysis.task import StructureAnalysisTask
from .structure_mirror.task import StructureMirrorTask
from .time_classification.task import TimeClassificationTask
from .timeline_extraction.task import TimelineExtractionTask
from .uppercase.task import UppercaseTask

__all__ = [
    "AuthorFoldersTask",
    "BudgetComputationTask",
    "CodeLocatingTask",
    "ContactInformationTask",
    "DatasetComparisonTask",
    "DebuggingTask",
    "DisputeReviewTask",
    "DuplicateNameTask",
    "DuplicatesSearchingTask",
    "EnglishTalentTask",
    "FileArrangementTask",
    "FileMergingTask",
    "FileSplittingTask",
    "FindMathPaperTask",
    "GradebasedScoreTask",
    "IndividualCommentsTask",
    "MusicReportTask",
    "OrganizeLegacyPapersTask",
    "OutputAnalysisTask",
    "PatternMatchingTask",
    "ProjectManagementTask",
    "RequirementsCompletionTask",
    "RequirementsWritingTask",
    "SizeClassificationTask",
    "SolutionTracingTask",
    "StructureAnalysisTask",
    "StructureMirrorTask",
    "TimeClassificationTask",
    "TimelineExtractionTask",
    "UppercaseTask",
]
