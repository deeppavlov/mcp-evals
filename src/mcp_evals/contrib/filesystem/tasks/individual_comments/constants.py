"""Constants for individual_comments task."""

# Expected data based on answer.csv
EXPECTED_DATA = {
    "Bill Harvey": ["0", "2", "3", "1", "1", "1"],
    "Michelle Jackson": ["0", "1", "2", "1", "1", "1"],
    "David Russel": ["2", "1", "1", "2", "1", "1"],
    "Tony Taylor": ["2", "0", "1", "2", "1", "1"],
}

# Expected header columns (excluding first column which can be anything)
EXPECTED_HEADER_COLUMNS = ["1.1", "1.3", "4.6", "4.16", "6.8", "6.16"]

EXPECTED_COLUMN_COUNT = 7  # First column + 6 clauses
