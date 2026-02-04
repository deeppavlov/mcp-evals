"""Duplicates Searching task for filesystem domain."""

import hashlib
from pathlib import Path


def calculate_file_hash(file_path: Path) -> str | None:
    """Calculate MD5 hash of file content."""
    try:
        with file_path.open("rb") as f:
            return hashlib.md5(f.read()).hexdigest()  # noqa: S324
    except (OSError, UnicodeDecodeError):
        return None
