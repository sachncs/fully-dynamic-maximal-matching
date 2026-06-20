"""Multiprocessing support for parallel update processing.

This module provides utilities for running multiple DynamicMaximalMatching
instances in parallel, useful for benchmarking and comparing modes.

**Engineering utility** -- not part of the paper's baseline algorithm.
"""

from __future__ import annotations

import multiprocessing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fdmm.simulation import random_update_sequence

if TYPE_CHECKING:
    pass


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run."""

    n: int
    mode: str
    updates: int
    elapsed_sec: float
    updates_per_sec: float
    matching_size: int
    is_maximal: bool
    phase_rebuilds: int
    subphase_rebuilds: int


def _run_benchmark_worker(
    n: int,
    mode: str,
    updates: int,
    seed: int,
) -> BenchmarkResult:
    """Worker function for parallel benchmark execution."""
    import time

    from fdmm.dynamic_matching import DynamicMaximalMatching

    algo = DynamicMaximalMatching(n, mode=mode)
    rng = __import__("random").Random(seed)
    seq = list(random_update_sequence(n, updates, rng))

    start = time.perf_counter()
    for op, u, v in seq:
        if op == "insert":
            algo.insert_edge(u, v)
        else:
            algo.delete_edge(u, v)
    elapsed = time.perf_counter() - start

    stats = algo.statistics()
    return BenchmarkResult(
        n=n,
        mode=mode,
        updates=updates,
        elapsed_sec=elapsed,
        updates_per_sec=updates / elapsed if elapsed > 0 else float("inf"),
        matching_size=stats["matching_size"],
        is_maximal=algo.is_maximal(),
        phase_rebuilds=stats.get("phase_rebuilds", 0),
        subphase_rebuilds=stats.get("subphase_rebuilds", 0),
    )


def run_parallel_benchmarks(
    configs: list[tuple[int, str, int, int]],
    max_workers: int | None = None,
) -> list[BenchmarkResult]:
    """Run multiple benchmarks in parallel.

    Args:
        configs: List of (n, mode, updates, seed) tuples.
        max_workers: Maximum number of parallel workers (default: CPU count).

    Returns:
        List of BenchmarkResult objects.

    Example:
        >>> configs = [
        ...     (100, "basic", 1000, 42),
        ...     (100, "multilevel", 1000, 42),
        ...     (200, "basic", 1000, 42),
        ... ]
        >>> results = run_parallel_benchmarks(configs)
        >>> for r in results:
        ...     print(f"{r.mode}: {r.updates_per_sec:.0f} ops/sec")
    """
    with multiprocessing.Pool(processes=max_workers) as pool:
        results = pool.starmap(
            _run_benchmark_worker,
            configs,
        )
    return list(results)


def compare_modes(
    n: int,
    updates: int,
    seed: int = 42,
    max_workers: int | None = None,
) -> dict[str, BenchmarkResult]:
    """Compare basic and multilevel modes on the same graph size.

    Args:
        n: Number of vertices.
        updates: Number of update operations.
        seed: Random seed for reproducibility.
        max_workers: Maximum parallel workers.

    Returns:
        Dict mapping mode name to BenchmarkResult.
    """
    configs = [
        (n, "basic", updates, seed),
        (n, "multilevel", updates, seed),
    ]
    results = run_parallel_benchmarks(configs, max_workers)
    return {r.mode: r for r in results}
