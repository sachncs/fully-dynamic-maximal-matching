"""Minimal demo of the FDMM algorithm.

Usage::

    python scripts/demo.py [--n N] [--mode {basic,multilevel}]

Example::

    python scripts/demo.py --n 10 --mode basic
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time

# Allow running the demo directly from the scripts/ directory.
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from fdmm.dynamic_matching import DynamicMaximalMatching


def run_demo(n: int, mode: str, num_updates: int) -> None:
    """Run a demo sequence of random insertions and deletions.

    Args:
        n: Number of vertices.
        mode: ``"basic"`` or ``"multilevel"``.
        num_updates: Total number of update operations.
    """
    print(f"=== FDMM Demo: n={n}, mode={mode}, updates={num_updates} ===\n")

    algo = DynamicMaximalMatching(n, mode=mode)
    rng = random.Random(42)
    edges: set[tuple[int, int]] = set()

    start = time.perf_counter()
    for step in range(num_updates):
        if rng.random() < 0.6 or not edges:
            # Insert a random edge
            u = rng.randrange(n)
            v = rng.randrange(n)
            if u != v:
                e = (min(u, v), max(u, v))
                if e not in edges:
                    edges.add(e)
                    algo.insert_edge(e[0], e[1])
        else:
            # Delete a random edge
            e = rng.choice(list(edges))
            edges.remove(e)
            algo.delete_edge(e[0], e[1])

        if not algo.is_maximal():
            print(f"ERROR: Matching is not maximal at step {step}!")
            return

    elapsed = time.perf_counter() - start
    stats = algo.statistics()

    print(f"Completed {num_updates} updates in {elapsed:.3f}s")
    print(f"Final graph edges: {stats['m']}")
    print(f"Matching size: {stats['matching_size']}")
    print(f"Rebuilds triggered: {num_updates // stats['phase_length']}")
    print(f"Maximal: {algo.is_maximal()}")
    print("\nDemo finished successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="FDMM Demo")
    parser.add_argument("--n", type=int, default=20, help="Number of vertices")
    parser.add_argument(
        "--mode", choices=["basic", "multilevel"], default="basic", help="Algorithm mode"
    )
    parser.add_argument(
        "--updates", type=int, default=200, help="Number of update operations"
    )
    args = parser.parse_args()
    run_demo(args.n, args.mode, args.updates)


if __name__ == "__main__":
    main()
