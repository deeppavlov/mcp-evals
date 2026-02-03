"""Custom evaluators for author_folders task."""

from .authors_2025_organization import Authors2025Organization
from .directories_exist import DirectoriesExist
from .frequent_authors_organization import FrequentAuthorsOrganization
from .naming_convention import NamingConvention
from .original_files_intact import OriginalFilesIntact

__all__ = [
    "Authors2025Organization",
    "DirectoriesExist",
    "FrequentAuthorsOrganization",
    "NamingConvention",
    "OriginalFilesIntact",
]
