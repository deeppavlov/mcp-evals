"""Filesystem tasks for MCP Universe evaluations."""

from .author_folders import AuthorFoldersTask
from .budget_computation import BudgetComputationTask
from .code_locating import CodeLocatingTask
from .contact_information import ContactInformationTask
from .dataset_comparison import DatasetComparisonTask
from .debugging import DebuggingTask
from .dispute_review import DisputeReviewTask
from .duplicate_name import DuplicateNameTask
from .duplicates_searching import DuplicatesSearchingTask
from .english_talent import EnglishTalentTask
from .file_arrangement import FileArrangementTask
from .file_merging import FileMergingTask
from .file_splitting import FileSplittingTask
from .find_math_paper import FindMathPaperTask
from .gradebased_score import GradebasedScoreTask
from .individual_comments import IndividualCommentsTask
from .music_report import MusicReportTask
from .organize_legacy_papers import OrganizeLegacyPapersTask
from .output_analysis import OutputAnalysisTask
from .pattern_matching import PatternMatchingTask
from .project_management import ProjectManagementTask
from .requirements_completion import RequirementsCompletionTask
from .requirements_writing import RequirementsWritingTask
from .size_classification import SizeClassificationTask
from .solution_tracing import SolutionTracingTask
from .structure_analysis import StructureAnalysisTask
from .structure_mirror import StructureMirrorTask
from .time_classification import TimeClassificationTask
from .timeline_extraction import TimelineExtractionTask
from .uppercase import UppercaseTask

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
