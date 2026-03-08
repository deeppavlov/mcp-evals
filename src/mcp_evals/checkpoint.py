"""Checkpoint state for resumable domain evaluation."""

from pathlib import Path


class Checkpoint:
    """Tracks which (scope, task) runs have completed for resumable evaluation.

    Keys are stored as "{scope}::{task_name}". The domain loads the checkpoint
    on enter and filters tasks by scope; the task lifecycle records keys on
    normal exit. When checkpoint_path is None, no checkpointing is performed.
    """

    def __init__(self, path: Path) -> None:
        """Initialize checkpoint with a file path.

        Args:
            path: File path for persistence (e.g. domain checkpoint file).
                  One key per line; created on first record_finished if missing.
        """
        self.path = path
        self._finished_keys: set[str] = set()

    def load(self) -> None:
        """Load finished keys from the checkpoint file.

        Idempotent: safe to call multiple times. Clears and repopulates
        _finished_keys from disk. If the file does not exist, _finished_keys
        remains empty.
        """
        self._finished_keys.clear()
        if not self.path.exists():
            return
        text = self.path.read_text(encoding="utf-8")
        for line in text.splitlines():
            key = line.strip()
            if key:
                self._finished_keys.add(key)

    def _key(self, scope: str, task_name: str) -> str:
        """Build the checkpoint key for a (scope, task_name) run."""
        return f"{scope}::{task_name}"

    def is_finished(self, scope: str, task_name: str) -> bool:
        """Return True if the run for this scope and task is already recorded."""
        return self._key(scope, task_name) in self._finished_keys

    def record_finished(self, scope: str, task_name: str) -> None:
        """Mark the run as finished and persist to the checkpoint file."""
        key = self._key(scope, task_name)
        if key in self._finished_keys:
            return
        self._finished_keys.add(key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(key + "\n")
