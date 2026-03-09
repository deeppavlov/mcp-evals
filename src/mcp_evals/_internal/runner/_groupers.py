"""Groupers: produce train/test splittings from a task count."""

from collections.abc import Iterator
from typing import Protocol

from ._splits import Splitting, hold_out_split, k_fold_split


class Grouper(Protocol):
    """Protocol for producing a sequence of train/test splittings."""

    def splittings(self, n_tasks: int) -> Iterator[Splitting]:
        """Yield splittings (train_indices, test_indices) for the given task count."""
        ...


class PlainGrouper:
    """Single splitting: no train, all tasks as test (inference-only)."""

    def splittings(self, n_tasks: int) -> Iterator[Splitting]:
        if n_tasks <= 0:
            return
        yield Splitting(train_indices=[], test_indices=list(range(n_tasks)))


class HoldOutGrouper:
    """Single train/test split with configurable test ratio."""

    def __init__(
        self,
        test_ratio: float = 0.2,
        random_state: int | None = None,
    ) -> None:
        self.test_ratio = test_ratio
        self.random_state = random_state

    def splittings(self, n_tasks: int) -> Iterator[Splitting]:
        yield hold_out_split(n_tasks, self.test_ratio, self.random_state)


class CVGrouper:
    """K-fold cross-validation splittings."""

    def __init__(
        self,
        n_splits: int = 5,
        random_state: int | None = None,
    ) -> None:
        self.n_splits = n_splits
        self.random_state = random_state

    def splittings(self, n_tasks: int) -> Iterator[Splitting]:
        yield from k_fold_split(n_tasks, self.n_splits, self.random_state)
