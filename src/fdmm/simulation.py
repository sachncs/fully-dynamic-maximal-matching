"""Simulation and replay utilities for dynamic update sequences.

These helpers are engineering utilities, not part of the paper's baseline
algorithm.  They allow reproducible experiments and stress tests.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from typing import TYPE_CHECKING

from fdmm.types import Vertex

if TYPE_CHECKING:
    from fdmm.dynamic_matching import DynamicMaximalMatching

Update = tuple[str, Vertex, Vertex]


def random_update_sequence(
    n: int,
    steps: int,
    rng: random.Random,
    existing: set[tuple[int, int]] | None = None,
) -> Iterator[Update]:
    """Yield a random sequence of insert/delete operations.

    Args:
        n: Number of vertices.
        steps: Number of operations to generate.
        rng: Seeded random number generator.
        existing: Optional initial edge set.

    Yields:
        Tuples ``("insert", u, v)`` or ``("delete", u, v)``.
    """
    edges: set[tuple[int, int]] = set(existing) if existing else set()
    yielded = 0
    while yielded < steps:
        u = rng.randrange(n)
        v = rng.randrange(n)
        if u == v:
            continue
        e = (min(u, v), max(u, v))
        if e not in edges:
            edges.add(e)
            yield ("insert", e[0], e[1])
        else:
            edges.remove(e)
            yield ("delete", e[0], e[1])
        yielded += 1


def replay_updates(algo: DynamicMaximalMatching, updates: list[Update]) -> None:
    """Replay a prepared update sequence on ``algo``.

    Args:
        algo: The dynamic matcher.
        updates: List of operations from :func:`random_update_sequence`.
    """
    for op, u, v in updates:
        if op == "insert":
            algo.insert_edge(u, v)
        elif op == "delete":
            algo.delete_edge(u, v)
        else:
            raise ValueError(f"Unknown operation: {op}")
