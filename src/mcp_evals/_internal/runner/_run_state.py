"""Run state persistence: task-level progress for resume after interruption."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import anyio
from anyio import Path as AnyioPath

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._splits import Splitting


Phase = Literal["train", "test"]

SPLITTING_FINGERPRINT_KEY = "splitting_fingerprint"
N_TASKS_KEY = "n_tasks"
ATTR_GLOBAL_INDEX = "_mcp_evals_global_index"

MIN_HEADER_LINES = 2
MIN_PARTS_SPLIT_PHASE_STARTED = 3
MIN_PARTS_SPLIT_FINISHED = 2
MIN_PARTS_TASK_FINISHED = 4


def _fingerprint(splittings: Sequence[Splitting]) -> list[tuple[int, int]]:
    """Stable fingerprint: (len(train), len(test)) per split."""
    return [(len(s.train_indices), len(s.test_indices)) for s in splittings]


def _fingerprint_to_line(fingerprint: list[tuple[int, int]]) -> str:
    """One line: space-separated 'len_train,len_test' per split."""
    return " ".join(f"{a},{b}" for a, b in fingerprint)


def _parse_fingerprint(line: str) -> list[tuple[int, int]]:
    """Parse fingerprint line back to list of (int, int)."""
    result: list[tuple[int, int]] = []
    for part in line.strip().split():
        a, b = part.split(",", 1)
        result.append((int(a), int(b)))
    return result


class RunState:
    """Persistent state for domain run: finished tasks and phase markers.

    Only the domain runner owns and updates this. Path is determined by
    experiment name. Uses async file I/O via anyio.Path.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = AnyioPath(path)
        self._n_tasks: int | None = None
        self._fingerprint: list[tuple[int, int]] | None = None
        self._phase_started: set[tuple[int, str]] = set()  # (split_idx, phase)
        self._split_finished: set[int] = set()
        self._task_finished: set[tuple[int, str, int]] = set()  # (split_idx, phase, global_index)
        self._header_written = False

    @classmethod
    async def load(
        cls,
        path: Path | str,
        n_tasks: int,
        splittings: Sequence[Splitting],
    ) -> RunState:
        """Load state from file; refuse to resume if fingerprint does not match."""
        state = cls(path)
        path_obj = AnyioPath(path)
        try:
            content = await path_obj.read_text()
        except FileNotFoundError:
            state._n_tasks = n_tasks
            state._fingerprint = _fingerprint(splittings)
            return state

        lines = content.strip().splitlines()
        if len(lines) < MIN_HEADER_LINES:
            state._n_tasks = n_tasks
            state._fingerprint = _fingerprint(splittings)
            return state

        # Header: n_tasks, splitting fingerprint
        first = lines[0].strip()
        second = lines[1].strip()
        if not first.startswith(f"{N_TASKS_KEY} ") or not second.startswith(f"{SPLITTING_FINGERPRINT_KEY} "):
            state._n_tasks = n_tasks
            state._fingerprint = _fingerprint(splittings)
            return state

        try:
            state._n_tasks = int(first.split(maxsplit=1)[1])
            state._fingerprint = _parse_fingerprint(second.split(maxsplit=1)[1])
        except (ValueError, IndexError):
            state._n_tasks = n_tasks
            state._fingerprint = _fingerprint(splittings)
            return state

        current_fp = _fingerprint(splittings)
        if state._n_tasks != n_tasks or state._fingerprint != current_fp:
            msg = (
                "Cannot resume: splittings or n_tasks changed "
                f"(stored n_tasks={state._n_tasks}, fingerprint={state._fingerprint}; "
                f"current n_tasks={n_tasks}, fingerprint={current_fp})"
            )
            raise ValueError(msg)

        state._header_written = True

        for event_line_ in lines[MIN_HEADER_LINES:]:
            event_line = event_line_.strip()
            if not event_line:
                continue
            parts = event_line.split()
            if len(parts) < MIN_PARTS_SPLIT_FINISHED:
                continue
            kind = parts[0]
            if kind == "split_phase_started" and len(parts) >= MIN_PARTS_SPLIT_PHASE_STARTED:
                with contextlib.suppress(ValueError):
                    split_idx = int(parts[1])
                    phase = parts[2]
                    if phase in ("train", "test"):
                        state._phase_started.add((split_idx, phase))
            elif kind == "split_finished" and len(parts) >= MIN_PARTS_SPLIT_FINISHED:
                with contextlib.suppress(ValueError):
                    state._split_finished.add(int(parts[1]))
            elif kind == "task_finished" and len(parts) >= MIN_PARTS_TASK_FINISHED:
                with contextlib.suppress(ValueError):
                    split_idx = int(parts[1])
                    phase = parts[2]
                    global_index = int(parts[3])
                    if phase in ("train", "test"):
                        state._task_finished.add((split_idx, phase, global_index))

        return state

    def has_split_phase_started(self, split_idx: int, phase: Phase) -> bool:
        """Return True if the start callback for this split/phase already ran successfully."""
        return (split_idx, phase) in self._phase_started

    def pending_indices(
        self,
        split_idx: int,
        phase: Phase,
        indices: Sequence[int],
    ) -> list[int]:
        """Return indices not yet marked as task_finished for this split/phase."""
        return [i for i in indices if (split_idx, phase, i) not in self._task_finished]

    async def mark_split_phase_started(self, split_idx: int, phase: Phase) -> None:
        """Append event (call only after the corresponding start callback succeeded)."""
        await self._append(f"split_phase_started {split_idx} {phase}")
        self._phase_started.add((split_idx, phase))

    async def mark_split_finished(self, split_idx: int) -> None:
        """Append event (call after start_testing for the next split succeeded)."""
        await self._append(f"split_finished {split_idx}")
        self._split_finished.add(split_idx)

    async def mark_task_finished(self, split_idx: int, phase: Phase, task_global_index: int) -> None:
        """Append event (call from task lifecycle on clean exit)."""
        await self._append(f"task_finished {split_idx} {phase} {task_global_index}")
        self._task_finished.add((split_idx, phase, task_global_index))

    async def _append(self, line: str) -> None:
        await self._ensure_header()
        async with await anyio.open_file(self._path, "a") as f:
            await f.write(line + "\n")

    async def _ensure_header(self) -> None:
        if self._header_written:
            return
        if self._n_tasks is None or self._fingerprint is None:
            return
        await self._path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"{N_TASKS_KEY} {self._n_tasks}\n{SPLITTING_FINGERPRINT_KEY} {_fingerprint_to_line(self._fingerprint)}\n"
        )
        async with await anyio.open_file(self._path, "a") as f:
            await f.write(header)
        self._header_written = True


def run_state_path(experiment_name: str, base_dir: Path | str | None = None) -> AnyioPath:
    """Path for the state file; default base is cwd with .mcp_evals_state subdir."""
    if base_dir is None:
        base_dir = Path.cwd() / ".mcp_evals_state"
    base_dir = AnyioPath(str(base_dir))
    return base_dir / f"{experiment_name}.progress"
