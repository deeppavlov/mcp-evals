"""Run state persistence: task-level progress for resume after interruption."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Annotated, Literal, NamedTuple

import anyio
from anyio import Path as AnyioPath
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ._splits import Splitting


Phase = Literal["train", "test"]


class SplitPhaseKey(NamedTuple):
    """Key for phase-started tracking: (split_idx, phase)."""

    split_idx: int
    phase: Phase


class TaskFinishedKey(NamedTuple):
    """Key for task-finished tracking: (split_idx, phase, task_name)."""

    split_idx: int
    phase: Phase
    task_name: str


class RunStateHeader(BaseModel):
    """First line of state file: n_tasks and splitting fingerprint for validation."""

    n_tasks: int
    splitting_fingerprint: list[list[int]] = Field(description="List of [len_train, len_test] per split.")


class SplitPhaseStartedEvent(BaseModel):
    """Emitted after start_training/start_testing callback ran successfully."""

    kind: Literal["split_phase_started"] = "split_phase_started"
    split_idx: int
    phase: Phase


class SplitFinishedEvent(BaseModel):
    """Emitted after start_testing for the next split ran (previous split left)."""

    kind: Literal["split_finished"] = "split_finished"
    split_idx: int


class TaskFinishedEvent(BaseModel):
    """Emitted from task lifecycle on clean exit (agent + evaluators ran without failure)."""

    kind: Literal["task_finished"] = "task_finished"
    split_idx: int
    phase: Phase
    task_name: str


RunStateEvent = Annotated[SplitPhaseStartedEvent | SplitFinishedEvent | TaskFinishedEvent, Field(discriminator="kind")]
_event_type_adapter: TypeAdapter[RunStateEvent] = TypeAdapter(RunStateEvent)


def _parse_event(line: str) -> RunStateEvent | None:
    """Parse a JSONL line into a RunStateEvent; return None for unknown/invalid."""
    line = line.strip()
    if not line:
        return None
    try:
        return _event_type_adapter.validate_json(line)
    except ValidationError:
        return None


def _fingerprint(splittings: Sequence[Splitting]) -> list[list[int]]:
    """Stable fingerprint: [len(train), len(test)] per split for JSON."""
    return [[len(s.train_indices), len(s.test_indices)] for s in splittings]


class RunState:
    """Persistent state for domain run: finished tasks and phase markers.

    Only the domain runner owns and updates this. Path is determined by
    experiment name. Uses JSONL + Pydantic and async file I/O via anyio.Path.
    """

    def __init__(self, path: AnyioPath | str) -> None:
        self._path = AnyioPath(path)
        self._n_tasks: int | None = None
        self._fingerprint: list[list[int]] | None = None
        self._phase_started: set[SplitPhaseKey] = set()
        self._split_finished: set[int] = set()
        self._task_finished: set[TaskFinishedKey] = set()
        self._header_written = False

    @classmethod
    async def load(
        cls,
        path: AnyioPath,
        n_tasks: int,
        splittings: Sequence[Splitting],
    ) -> RunState:
        """Load state from JSONL file; refuse to resume if fingerprint does not match."""
        state = cls(path)
        try:
            content = await path.read_text()
        except FileNotFoundError:
            state._n_tasks = n_tasks
            state._fingerprint = _fingerprint(splittings)
            return state

        lines = content.strip().splitlines()
        if not lines:
            state._n_tasks = n_tasks
            state._fingerprint = _fingerprint(splittings)
            return state

        try:
            header = RunStateHeader.model_validate_json(lines[0])
        except ValidationError:
            state._n_tasks = n_tasks
            state._fingerprint = _fingerprint(splittings)
            return state

        state._n_tasks = header.n_tasks
        state._fingerprint = header.splitting_fingerprint
        current_fp = _fingerprint(splittings)
        if state._n_tasks != n_tasks or state._fingerprint != current_fp:
            msg = (
                "Cannot resume: splittings or n_tasks changed "
                f"(stored n_tasks={state._n_tasks}, fingerprint={state._fingerprint}; "
                f"current n_tasks={n_tasks}, fingerprint={current_fp})"
            )
            raise ValueError(msg)

        state._header_written = True

        for event_line in lines[1:]:
            event = _parse_event(event_line)
            if event is None:
                continue
            if isinstance(event, SplitPhaseStartedEvent):
                state._phase_started.add(SplitPhaseKey(event.split_idx, event.phase))
            elif isinstance(event, SplitFinishedEvent):
                state._split_finished.add(event.split_idx)
            elif isinstance(event, TaskFinishedEvent):
                state._task_finished.add(TaskFinishedKey(event.split_idx, event.phase, event.task_name))

        return state

    def has_split_phase_started(self, split_idx: int, phase: Phase) -> bool:
        """Return True if the start callback for this split/phase already ran successfully."""
        return SplitPhaseKey(split_idx, phase) in self._phase_started

    def pending_indices(
        self,
        split_idx: int,
        phase: Phase,
        indices: Sequence[int],
        task_names: Sequence[str],
    ) -> list[int]:
        """Return indices not yet marked as task_finished for this split/phase.

        task_names[i] is the name of the task at index i in the full task list.
        """
        return [i for i in indices if TaskFinishedKey(split_idx, phase, task_names[i]) not in self._task_finished]

    async def mark_split_phase_started(self, split_idx: int, phase: Phase) -> None:
        """Append event (call only after the corresponding start callback succeeded)."""
        event = SplitPhaseStartedEvent(split_idx=split_idx, phase=phase)
        await self._append_event(event)
        self._phase_started.add(SplitPhaseKey(split_idx, phase))

    async def mark_split_finished(self, split_idx: int) -> None:
        """Append event (call after start_testing for the next split succeeded)."""
        event = SplitFinishedEvent(split_idx=split_idx)
        await self._append_event(event)
        self._split_finished.add(split_idx)

    async def mark_task_finished(self, split_idx: int, phase: Phase, task_name: str) -> None:
        """Append event (call from task lifecycle on clean exit)."""
        event = TaskFinishedEvent(split_idx=split_idx, phase=phase, task_name=task_name)
        await self._append_event(event)
        self._task_finished.add(TaskFinishedKey(split_idx, phase, task_name))

    async def _append_event(self, event: RunStateEvent) -> None:
        await self._ensure_header()
        line = event.model_dump_json(exclude_none=True)
        async with await anyio.open_file(self._path, "a") as f:
            await f.write(line + "\n")

    async def _ensure_header(self) -> None:
        if self._header_written:
            return
        if self._n_tasks is None or self._fingerprint is None:
            return
        await self._path.parent.mkdir(parents=True, exist_ok=True)
        header = RunStateHeader(n_tasks=self._n_tasks, splitting_fingerprint=self._fingerprint)
        line = header.model_dump_json(exclude_none=True) + "\n"
        async with await anyio.open_file(self._path, "a") as f:
            await f.write(line)
        self._header_written = True

    async def clear(self) -> None:
        """Remove the state file if it exists (e.g. after a full run)."""
        with contextlib.suppress(FileNotFoundError):
            await self._path.unlink()


async def run_state_path(
    experiment_name: str,
    state_dir: AnyioPath | Path | str | None = None,
) -> AnyioPath:
    """Path for the state file; default base is cwd with .mcp_evals_state subdir."""
    if state_dir is not None and not isinstance(state_dir, AnyioPath):
        state_dir = AnyioPath(state_dir)
    base_dir = state_dir or await AnyioPath.cwd()
    resolved = base_dir / ".mcp_evals_state"
    return AnyioPath(str(resolved / f"{experiment_name}.jsonl"))
