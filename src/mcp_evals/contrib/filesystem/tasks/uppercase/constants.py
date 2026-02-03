"""Constants for uppercase task."""

# Expected word counts based on answer.md
# Special case: file_06.txt can be 21 or 22
EXPECTED_COUNTS = [22, 22, 22, 22, 18, 22, 22, 22, 18, 20]

# Expected files
EXPECTED_FILES = [f"file_{i:02d}.txt" for i in range(1, 11)]
