# ruff: noqa: S311

"""Split utilities for hold-out and K-fold (stdlib-only, no sklearn)."""

import random
from collections.abc import Iterator
from typing import NamedTuple


class Splitting(NamedTuple):
    """A single train/test split: train_indices and test_indices."""

    train_indices: list[int]
    test_indices: list[int]


def hold_out_split(
    n_tasks: int,
    test_ratio: float,
    random_state: int | None = None,
) -> Splitting:
    """Split indices into train and test.

    Returns a Splitting(train_indices, test_indices). If random_state is set,
    indices are shuffled first for reproducibility; otherwise the last test_ratio
    fraction is used as test (deterministic).
    """
    if n_tasks <= 0:
        return Splitting(train_indices=[], test_indices=[])
    indices = list(range(n_tasks))
    if random_state is not None:
        rng = random.Random(random_state)
        rng.shuffle(indices)
    n_test = max(1, int(n_tasks * test_ratio)) if n_tasks >= 1 else 0
    n_test = min(n_test, n_tasks)
    test_indices = indices[-n_test:] if n_test else []
    train_indices = indices[: n_tasks - n_test] if n_test < n_tasks else indices
    return Splitting(train_indices=train_indices, test_indices=test_indices)


def k_fold_split(
    n_tasks: int,
    n_splits: int,
    random_state: int | None = None,
) -> Iterator[Splitting]:
    """Yield a Splitting (train_indices, test_indices) for each fold.

    Each fold uses a disjoint chunk as test; the rest is train. If random_state
    is set, indices are shuffled first. n_splits is capped at n_tasks.
    """
    if n_tasks <= 0 or n_splits <= 0:
        return
    indices = list(range(n_tasks))
    if random_state is not None:
        rng = random.Random(random_state)
        rng.shuffle(indices)
    k = min(n_splits, n_tasks)
    fold_size = n_tasks // k
    remainder = n_tasks % k
    start = 0
    for i in range(k):
        # First 'remainder' folds get fold_size+1 test samples
        test_len = fold_size + (1 if i < remainder else 0)
        test_indices = indices[start : start + test_len]
        train_indices = indices[:start] + indices[start + test_len :]
        yield Splitting(train_indices=train_indices, test_indices=test_indices)
        start += test_len
