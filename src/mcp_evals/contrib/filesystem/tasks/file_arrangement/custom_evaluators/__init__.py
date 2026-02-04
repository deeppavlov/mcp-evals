"""Custom evaluators for file_arrangement task."""

from .no_duplicate_required_files import NoDuplicateRequiredFiles
from .required_files_in_correct_folders import RequiredFilesInCorrectFolders

__all__ = [
    "NoDuplicateRequiredFiles",
    "RequiredFilesInCorrectFolders",
]
