"""Public type aliases and shared callback context types for mcp_evals."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic_ai import AgentRunResult

from mcp_evals.task import Task

type DepsMaker = Callable[[Task[Any, Any]], AbstractAsyncContextManager[object]]


type PhaseKind = Literal["train", "test"]


@dataclass()
class RunContext:
    """Runner context passed to training/testing callbacks."""

    phase_to_tasks: dict[str, list[Task[Any, Any]]]
    current_phase_kind: PhaseKind | None = field(default=None, init=False)
    current_split_idx: int | None = field(default=None, init=False)

    def set_current_phase(self, phase_kind: PhaseKind, split_idx: int) -> None:
        """Set active phase for helper methods and callback consumers."""
        phase_name = self._phase_name(phase_kind, split_idx)
        if phase_name not in self.phase_to_tasks:
            msg = f"Unknown phase: {phase_name!r}"
            raise ValueError(msg)
        self.current_phase_kind = phase_kind
        self.current_split_idx = split_idx

    @property
    def phase_name(self) -> str:
        """Current phase name (for example: 'train_0', 'test_1')."""
        if self.current_phase_kind is None or self.current_split_idx is None:
            msg = "Current phase is not set"
            raise ValueError(msg)
        return self._phase_name(self.current_phase_kind, self.current_split_idx)

    @property
    def phase_kind(self) -> PhaseKind:
        """Current phase kind: 'train' or 'test'."""
        if self.current_phase_kind is None:
            msg = "Current phase is not set"
            raise ValueError(msg)
        return self.current_phase_kind

    @property
    def split_idx(self) -> int:
        """Current phase split index."""
        if self.current_split_idx is None:
            msg = "Current phase is not set"
            raise ValueError(msg)
        return self.current_split_idx

    def get_phase_tasks(
        self, *, phase_kind: PhaseKind | None = None, split_idx: int | None = None
    ) -> tuple[Task[Any, Any], ...]:
        """Return tasks for the provided phase (or current phase by default)."""
        resolved_kind, resolved_idx = self._resolve_phase(phase_kind, split_idx)
        return tuple(self.phase_to_tasks[self._phase_name(resolved_kind, resolved_idx)])

    def get_training_tasks(
        self, *, phase_kind: PhaseKind | None = None, split_idx: int | None = None
    ) -> tuple[Task[Any, Any], ...]:
        """Return training tasks for this phase (train_i for both train_i/test_i)."""
        _, resolved_idx = self._resolve_phase(phase_kind, split_idx)
        train_phase = self._phase_name("train", resolved_idx)
        if train_phase not in self.phase_to_tasks:
            msg = f"Training phase not found for split {resolved_idx}"
            raise ValueError(msg)
        return tuple(self.phase_to_tasks[train_phase])

    @staticmethod
    def _phase_name(phase_kind: PhaseKind, split_idx: int) -> str:
        if split_idx < 0:
            msg = f"split_idx must be >= 0, got {split_idx}"
            raise ValueError(msg)
        return f"{phase_kind}_{split_idx}"

    def _resolve_phase(self, phase_kind: PhaseKind | None, split_idx: int | None) -> tuple[PhaseKind, int]:
        if phase_kind is None and split_idx is None:
            return self.phase_kind, self.split_idx
        if phase_kind is None or split_idx is None:
            msg = "phase_kind and split_idx must be provided together"
            raise ValueError(msg)
        phase_name = self._phase_name(phase_kind, split_idx)
        if phase_name not in self.phase_to_tasks:
            msg = f"Unknown phase: {phase_name!r}"
            raise ValueError(msg)
        return phase_kind, split_idx


type TrainingTestingCallback = Callable[[RunContext], Awaitable[None]]

type EvaluatedFn = (
    Callable[[Task[Any, Any]], Awaitable[AgentRunResult[Any]]] | Callable[[Task[Any, Any]], AgentRunResult[Any]]
)

type RunResultProcessor = Callable[[Task[Any, Any], AgentRunResult[Any], object], Awaitable[None]]
