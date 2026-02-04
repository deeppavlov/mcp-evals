"""Helper functions for pattern_matching task."""

from pathlib import Path


def find_30_plus_char_matches(test_dir: Path) -> dict[str, int]:
    """Find all matches with 30 or more characters between files and large_file.txt."""
    large_file = test_dir / "large_file.txt"
    if not large_file.exists():
        return {}

    large_content = large_file.read_text(encoding="utf-8")
    matches: dict[str, int] = {}

    # Check each file from file_01.txt to file_20.txt
    for i in range(1, 21):
        filename = f"file_{i:02d}.txt"
        file_path = test_dir / filename

        if not file_path.exists():
            continue

        file_content = file_path.read_text(encoding="utf-8")

        # Find the longest matching substring (30+ characters)
        longest_match = ""
        longest_match_start = -1

        # Check all possible substrings in the file
        for start_pos in range(len(file_content)):
            for end_pos in range(start_pos + 30, len(file_content) + 1):  # At least 30 characters
                substring = file_content[start_pos:end_pos]

                # Check if this substring exists in large_file.txt
                if substring in large_content and len(substring) > len(longest_match):
                    longest_match = substring
                    # Find the position in large_file.txt where this substring starts
                    large_start_pos = large_content.find(substring)
                    longest_match_start = large_start_pos + 1  # 1-indexed

        # If we found a match of 30+ characters, record it
        if longest_match and len(longest_match) >= 30:  # noqa: PLR2004
            matches[filename] = longest_match_start

    return matches
