"""Constants for time_classification task."""

# Expected directory structure
EXPECTED_STRUCTURE = {
    "07": {
        "09": ["sg.jpg"],
        "25": ["bus.MOV"],
        "26": ["road.MOV"],
    },
    "08": {
        "06": ["bear.jpg", "bridge.jpg", "random_file_1.txt", "random_file_2.txt", "random_file_3.txt"],
    },
}

# Month mapping (numeric and alphabetic)
MONTH_MAPPING = {
    "07": ["07", "7", "jul", "Jul", "JUL"],
    "08": ["08", "8", "aug", "Aug", "AUG"],
}

# Day mapping
DAY_MAPPING = {
    "09": ["09", "9"],
    "25": ["25"],
    "26": ["26"],
    "06": ["06", "6"],
}

# System files to ignore
SYSTEM_FILES = [".DS_Store", "Thumbs.db", ".DS_Store?", "._.DS_Store", "metadata_analyse.txt"]

TOTAL_EXPECTED_FILES = sum(len(files) for days in EXPECTED_STRUCTURE.values() for files in days.values())
