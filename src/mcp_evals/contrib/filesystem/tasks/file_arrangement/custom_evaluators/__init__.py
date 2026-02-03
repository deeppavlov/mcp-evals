"""Custom evaluators for file_arrangement task."""

from .archives_folder_files import ArchivesFolderFiles
from .folder_structure import FolderStructure
from .life_folder_files import LifeFolderFiles
from .no_duplicate_required_files import NoDuplicateRequiredFiles
from .others_folder_exists import OthersFolderExists
from .required_files_in_correct_folders import RequiredFilesInCorrectFolders
from .temp_folder_files import TempFolderFiles
from .work_folder_files import WorkFolderFiles

__all__ = [
    "ArchivesFolderFiles",
    "FolderStructure",
    "LifeFolderFiles",
    "NoDuplicateRequiredFiles",
    "OthersFolderExists",
    "RequiredFilesInCorrectFolders",
    "TempFolderFiles",
    "WorkFolderFiles",
]
