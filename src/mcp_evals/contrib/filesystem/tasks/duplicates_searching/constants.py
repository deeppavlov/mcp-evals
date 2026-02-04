"""Constants for duplicates_searching task."""

# Expected duplicate file groups
EXPECTED_DUPLICATE_GROUPS = {
    "group1": ["file_01.txt", "file_02.txt"],
    "group2": ["file_03.txt", "file_04.txt"],
    "group3": ["file_07.txt", "file_08.txt"],
    "group4": ["file_10.txt", "file_11.txt"],
    "group5": ["file_13.txt", "file_14.txt"],
    "group6": ["file_15.txt", "file_16.txt"],
    "group7": ["file_18.txt", "file_19.txt"],
}

# Expected unique files that should remain in original location
EXPECTED_UNIQUE_FILES = [
    "file_05.txt",
    "file_06.txt",
    "file_09.txt",
    "file_12.txt",
    "file_17.txt",
    "file_20.txt",
]
