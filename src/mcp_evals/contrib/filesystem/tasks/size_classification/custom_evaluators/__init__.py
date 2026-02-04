"""Custom evaluators for size_classification task."""

from .file_classification import FileClassification
from .file_sizes import FileSizes

__all__ = [
    "FileClassification",
    "FileSizes",
]
