"""Constants for solution_tracing task."""

# Expected data based on answer.csv
EXPECTED_DATA = {
    "version_number": ["5", "6", "7", "8"],
    "name": ["Bill Harvey", "Michelle Jackson", "Michelle Jackson", "Tony Taylor"],
}

# Expected header columns (excluding first column which can be anything)
EXPECTED_HEADER_COLUMNS = ["4.6", "4.16", "6.8", "6.16"]

EXPECTED_COLUMN_COUNT = 5  # First column + 4 clauses
