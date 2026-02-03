"""Custom evaluators for structure_analysis task."""

from .depth_analysis import DepthAnalysis
from .file_statistics import FileStatistics
from .file_type_classification import FileTypeClassification

__all__ = [
    "DepthAnalysis",
    "FileStatistics",
    "FileTypeClassification",
]
