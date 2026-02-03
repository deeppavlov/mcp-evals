"""Custom evaluators for organize_legacy_papers task."""

from .author_extraction import AuthorExtraction
from .directory_structure import DirectoryStructure
from .index_files import IndexFiles
from .papers_moved import PapersMoved
from .papers_remain import PapersRemain
from .sorting import Sorting
from .summary_file import SummaryFile

__all__ = [
    "AuthorExtraction",
    "DirectoryStructure",
    "IndexFiles",
    "PapersMoved",
    "PapersRemain",
    "Sorting",
    "SummaryFile",
]
