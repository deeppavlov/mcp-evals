"""Utility functions for timeline_extraction task."""

import re

from mcp_evals.contrib.filesystem.tasks.timeline_extraction.constants import EXPECTED_ENTRIES


def _has_path_like_content(line: str) -> bool:
    """Check if a line contains path-like content."""
    # Method 1: Split into words and look for path-like content
    words = line.split()
    for word in words:
        if ("/" in word or "." in word) and not re.match(r"^\d{4}-\d{2}-\d{2}$", word.strip()):
            return True

    # Method 2: Check if line contains path-like content with colon separator
    if ":" in line:
        parts = line.split(":")
        for part in parts:
            if ("/" in part or "." in part) and not re.match(r"^\d{4}-\d{2}-\d{2}$", part.strip()):
                return True

    return False


def _extract_path_from_line(line: str) -> str | None:
    """Extract file path from a timeline line."""
    words = line.split()
    for word in words:
        if ("/" in word or "." in word) and not re.match(r"^\d{4}-\d{2}-\d{2}$", word.strip()):
            return word
    return None


def _check_missing_entries(actual_lines: list[str]) -> list[str]:
    """Check for missing expected entries."""
    missing_entries = []
    for expected in EXPECTED_ENTRIES:
        expected_path, expected_date = expected.split(":")
        found = False

        for actual_line in actual_lines:
            if expected_path in actual_line and expected_date in actual_line:
                found = True
                break

        if not found:
            missing_entries.append(expected)
    return missing_entries


def _check_extra_entries(actual_lines: list[str]) -> list[str]:
    """Check for extra unexpected entries."""
    extra_entries = []
    for actual_line in actual_lines:
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", actual_line)
        if not date_match:
            continue

        actual_date = date_match.group()
        actual_path = _extract_path_from_line(actual_line)

        if not actual_path:
            continue

        # Find if this line matches any expected entry
        found_expected = False
        for expected in EXPECTED_ENTRIES:
            expected_path, expected_date = expected.split(":")
            if expected_path in actual_path and actual_date == expected_date:
                found_expected = True
                break

        if not found_expected:
            extra_entries.append(actual_line)
    return extra_entries


def _extract_file_path_from_line(line: str) -> str | None:
    """Extract file path from a timeline line and check if it exists."""
    # Method 1: Split by colon and check each part
    if ":" in line:
        parts = line.split(":")
        for part_ in parts:
            part = part_.strip()
            if part and ("/" in part or "." in part) and not re.match(r"^\d{4}-\d{2}-\d{2}$", part):
                return part

    # Method 2: Split into words and look for path-like content
    words = line.split()
    for word in words:
        word_ = word.strip()
        if ("/" in word_ or "." in word_) and not re.match(r"^\d{4}-\d{2}-\d{2}$", word_):
            return word_

    # Method 3: Use regex to find path-like patterns
    path_matches = re.findall(r"[a-zA-Z0-9_\-\.\/]+/[a-zA-Z0-9_\-\.\/]+", line)
    for match in path_matches:
        if "." in match or "/" in match:
            return str(match)

    return None
