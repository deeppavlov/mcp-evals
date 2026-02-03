"""Constants for size_classification task."""

# Expected file classification
EXPECTED_CLASSIFICATION = {
    "small_files": ["random_file_1.txt", "random_file_3.txt"],
    "medium_files": ["random_file_2.txt"],
    "large_files": ["bear.jpg", "sg.jpg", "road.MOV", "bus.MOV", "bridge.jpg"],
}

REQUIRED_DIRS = ["small_files", "medium_files", "large_files"]

# System files to ignore
SYSTEM_FILES = [".DS_Store", "Thumbs.db", ".DS_Store?", "._.DS_Store"]

# Size thresholds
SMALL_FILE_MAX = 299  # < 300 bytes
MEDIUM_FILE_MIN = 300  # 300-700 bytes (inclusive)
MEDIUM_FILE_MAX = 700
LARGE_FILE_MIN = 701  # > 700 bytes

# Size ranges
SIZE_RANGES = {
    "small_files": (0, SMALL_FILE_MAX),
    "medium_files": (MEDIUM_FILE_MIN, MEDIUM_FILE_MAX),
    "large_files": (LARGE_FILE_MIN, float("inf")),
}

TOTAL_EXPECTED_FILES = sum(len(files) for files in EXPECTED_CLASSIFICATION.values())
