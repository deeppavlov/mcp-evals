"""Constants for organize_legacy_papers task."""

# Expected paper distribution
EXPECTED_PAPERS = {
    "2017": ["1707.06347.html"],
    "2021": ["2105.04165.html"],
    "2022": ["2201.11903.html"],
    "2023": [
        "2303.08774.html",
        "2306.08640.html",
        "2310.02255.html",
        "2310.08446.html",
        "2312.00849.html",
        "2312.07533.html",
        "2312.11805.html",
    ],
}

EXPECTED_YEARS = ["2017", "2021", "2022", "2023"]

EXPECTED_COUNTS = {
    "2017": 1,
    "2021": 1,
    "2022": 1,
    "2023": 7,
}

# Constants for year parsing
MIN_ARXIV_ID_LENGTH = 2
YEAR_THRESHOLD_2024 = 24
MAX_AUTHORS_FOR_DISPLAY = 3
