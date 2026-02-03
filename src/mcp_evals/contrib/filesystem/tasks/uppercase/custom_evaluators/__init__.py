"""Custom evaluators for uppercase task."""

from .all_files_are_included import AllFilesAreIncluded
from .answer_format import AnswerFormat
from .uppercase_content import UppercaseContent
from .uppercase_directory_exists import UppercaseDirectoryExists
from .uppercase_files_exist import UppercaseFilesExist
from .word_counts_are_correct import WordCountsAreCorrect

__all__ = [
    "AllFilesAreIncluded",
    "AnswerFormat",
    "UppercaseContent",
    "UppercaseDirectoryExists",
    "UppercaseFilesExist",
    "WordCountsAreCorrect",
]
