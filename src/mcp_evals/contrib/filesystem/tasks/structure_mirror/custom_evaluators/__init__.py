"""Custom evaluators for structure_mirror task."""

from .mirror_directory_exists import MirrorDirectoryExists
from .mirror_structure_completeness import MirrorStructureCompleteness
from .no_files_copied import NoFilesCopied

__all__ = [
    "MirrorDirectoryExists",
    "MirrorStructureCompleteness",
    "NoFilesCopied",
]
