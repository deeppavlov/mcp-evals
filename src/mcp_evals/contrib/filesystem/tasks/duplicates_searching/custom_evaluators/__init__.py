"""Custom evaluators for duplicates_searching task."""

from .content_integrity import ContentIntegrity
from .duplicate_files_moved import DuplicateFilesMoved
from .no_duplicates_in_original import NoDuplicatesInOriginal
from .unique_files_remain import UniqueFilesRemain

__all__ = [
    "ContentIntegrity",
    "DuplicateFilesMoved",
    "NoDuplicatesInOriginal",
    "UniqueFilesRemain",
]
