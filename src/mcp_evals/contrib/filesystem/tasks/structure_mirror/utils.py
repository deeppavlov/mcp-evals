"""Structure Mirror task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.tasks.structure_mirror.constants import MIRROR_DIR_NAME


def find_mirror_directory(work_dir: Path) -> Path | None:
    """Find the mirror directory."""
    mirror_dir = work_dir / MIRROR_DIR_NAME
    if mirror_dir.exists() and mirror_dir.is_dir():
        return mirror_dir
    return None
