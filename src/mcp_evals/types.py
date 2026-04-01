"""Public type aliases and shared callback context types for mcp_evals."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic_ai import AgentRunResult

from mcp_evals.task import Task

type DepsMaker = Callable[[Task[Any, Any]], AbstractAsyncContextManager[object]]


type PhaseKind = Literal["train", "test"]


@dataclass(slots=True)
class RunContext:
    """Runner context passed to training/testing callbacks."""

    phase_to_tasks: dict[str, list[Task[Any, Any]]]
    current_phase: str = field(default="", init=False)

    def set_current_phase(self, phase_name: str) -> None:
        """Set active phase for helper methods and callback consumers."""
        self._parse_phase_name(phase_name)
        if phase_name not in self.phase_to_tasks:
            msg = f"Unknown phase: {phase_name!r}"
            raise ValueError(msg)
        self.current_phase = phase_name

    @property
    def phase_name(self) -> str:
        """Current phase name (for example: 'train_0', 'test_1')."""
        if not self.current_phase:
            msg = "Current phase is not set"
            raise ValueError(msg)
        return self.current_phase

    @property
    def phase_kind(self) -> PhaseKind:
        """Current phase kind: 'train' or 'test'."""
        kind, _ = self._parse_phase_name(self.phase_name)
        return kind

    @property
    def split_idx(self) -> int:
        """Current phase split index."""
        _, split_idx = self._parse_phase_name(self.phase_name)
        return split_idx

    def get_phase_tasks(self, phase_name: str | None = None) -> tuple[Task[Any, Any], ...]:
        """Return tasks for the provided phase (or current phase by default)."""
        resolved_phase = self._resolve_phase_name(phase_name)
        return tuple(self.phase_to_tasks[resolved_phase])

    def get_training_tasks(self, phase_name: str | None = None) -> tuple[Task[Any, Any], ...]:
        """Return training tasks for this phase (train_i for both train_i/test_i)."""
        resolved_phase = self._resolve_phase_name(phase_name)
        _, split_idx = self._parse_phase_name(resolved_phase)
        train_phase = f"train_{split_idx}"
        if train_phase not in self.phase_to_tasks:
            msg = f"Training phase not found for split {split_idx}"
            raise ValueError(msg)
        return tuple(self.phase_to_tasks[train_phase])

    @staticmethod
    def _parse_phase_name(phase_name: str) -> tuple[PhaseKind, int]:
        parts = phase_name.split("_", maxsplit=1)
        if len(parts) != 2:
            msg = f"Invalid phase name format: {phase_name!r}"
            raise ValueError(msg)
        kind_raw, split_raw = parts
        if kind_raw not in ("train", "test") or not split_raw.isdigit():
            msg = f"Invalid phase name format: {phase_name!r}"
            raise ValueError(msg)
        return kind_raw, int(split_raw)

    def _resolve_phase_name(self, phase_name: str | None) -> str:
        if phase_name is None:
            return self.phase_name
        self._parse_phase_name(phase_name)
        if phase_name not in self.phase_to_tasks:
            msg = f"Unknown phase: {phase_name!r}"
            raise ValueError(msg)
        return phase_name


type TrainingTestingCallback = Callable[[RunContext], Awaitable[None]]

type EvaluatedFn = (
    Callable[[Task[Any, Any]], Awaitable[AgentRunResult[Any]]] | Callable[[Task[Any, Any]], AgentRunResult[Any]]
)

type RunResultProcessor = Callable[[Task[Any, Any], AgentRunResult[Any], object], Awaitable[None]]
