"""Custom evaluators for structure_mirror task."""

from .mirror_structure_completeness import MirrorStructureCompleteness
from .no_files_copied import NoFilesCopied

__all__ = [
    "MirrorStructureCompleteness",
    "NoFilesCopied",
]
