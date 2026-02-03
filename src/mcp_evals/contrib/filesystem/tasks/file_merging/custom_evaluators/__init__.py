"""Custom evaluators for file_merging task."""

from .alphabetical_order import AlphabeticalOrder
from .correct_files_selected import CorrectFilesSelected
from .file_content_integrity import FileContentIntegrity
from .filename_headers import FilenameHeaders

__all__ = [
    "AlphabeticalOrder",
    "CorrectFilesSelected",
    "FileContentIntegrity",
    "FilenameHeaders",
]

