# FDMM — Fully Dynamic Maximal Matching

[![CI](https://github.com/sachn-cs/fully-dynamic-maximal-matching/actions/workflows/ci.yml/badge.svg)](https://github.com/sachn-cs/fully-dynamic-maximal-matching/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sachn-cs/fully-dynamic-maximal-matching/branch/master/graph/badge.svg)](https://codecov.io/gh/sachn-cs/fully-dynamic-maximal-matching)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Python reproduction of *"A Faster Deterministic Algorithm for Fully Dynamic
> Maximal Matching"* (arXiv:2605.00797v1, Chuzhoy–Khanna–Song, STOC 2026).

## Overview

This package implements a deterministic algorithm that maintains a **maximal
matching** in an undirected graph under a sequence of online edge insertions
and deletions.  The adversary may be adaptive.  The paper achieves amortised
update time :math:`n^{1/2+o(1)}`, improving the previous deterministic bound.

### Key Features

* **Basic mode** — :math:`\tilde O(n^{2/3})` amortised update time (single-level
  :math:`z`-subgraph system).
* **Multi-level mode** — :math:`n^{1/2+o(1)}` amortised update time (recursive
  :math:`k`-level system with :math:`k = \Theta(\log n)`).
* Deterministic :math:`(\Delta+1)`-edge-colouring (Vizing's theorem).
* Comprehensive invariant checks and maximality verification.
* Explicit update-work counters for empirical cost auditing.
* Zero runtime dependencies; pure Python.

## Installation

Requires Python ≥ 3.10.

```bash
pip install -e ".[dev]"
```

For development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start

```python
from fdmm import DynamicMaximalMatching

# Initialise on 100 vertices in basic mode
algo = DynamicMaximalMatching(n=100, mode="basic")

# Insert edges
algo.insert_edge(0, 1)
algo.insert_edge(2, 3)

# Delete edges
algo.delete_edge(0, 1)

# Query
assert algo.is_maximal()
print("Matching size:", algo.matching_size())
print("Stats:", algo.statistics())
```

## Usage

### Command-Line Demo

```bash
python scripts/demo.py --n 20 --mode basic --updates 200
python scripts/demo.py --n 50 --mode multilevel --updates 500
```

Or via the installed entry point:

```bash
fdmm --n 20 --mode basic --updates 200
```

### API

#### `DynamicMaximalMatching(n, mode="basic")`

* `insert_edge(u, v)` — insert an undirected edge and repair the matching.
* `delete_edge(u, v)` — delete an undirected edge and repair the matching.
* `get_matching()` — return a copy of the current maximal matching.
* `is_maximal()` — verify that the current matching is maximal.
* `matching_size()` — number of edges in the matching.
* `statistics()` — runtime statistics (n, m, matching size, updates,
  accountant counters, etc.).

## Project Structure

```
fdmm/
├── pyproject.toml
├── README.md
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── fdmm/
│       ├── __init__.py
│       ├── types.py              # Type aliases and helpers
│       ├── graph.py              # DynamicGraph
│       ├── matching.py           # Greedy matcher and partner helpers
│       ├── edge_coloring.py      # Vizing edge colouring
│       ├── z_system.py           # ZSubgraphSystem + MultiLevelSystem + build_z_system
│       ├── dynamic_matching.py   # Main algorithm
│       ├── updates.py            # Insertion / deletion / rematch handlers
│       ├── invariants.py         # Standalone invariant checkers
│       ├── accounting.py         # Explicit update-work counters
│       ├── simulation.py         # Replay and random generators
│       └── cli.py                # Command-line entry point
├── tests/
│   └── test_fdmm.py          # Comprehensive unit tests
├── benchmarks/
│   └── bench_fdmm.py         # Lightweight throughput benchmark
├── scripts/
│   └── demo.py               # Runnable demo
├── examples/
│   ├── example_basic.py
│   └── example_multilevel.py
└── docs/
    ├── index.md              # API documentation
    ├── paper_restatement.md  # Parsed paper content + UNKNOWNs
    └── audit_report.md       # Codebase vs. paper audit
```

## Running Tests

```bash
pytest tests/ -v
```

All tests verify that the maintained matching is maximal after every
operation.  Invariant checks are included for the :math:`z`-subgraph system.

## Replaying Update Sequences

```python
from fdmm import DynamicMaximalMatching
from fdmm.simulation import random_update_sequence, replay_updates
import random

algo = DynamicMaximalMatching(50, mode="basic")
rng = random.Random(42)
updates = list(random_update_sequence(50, 200, rng))
replay_updates(algo, updates)
assert algo.is_maximal()
print(algo.statistics())
```

## Interpreting Update Counters

`statistics()` includes counters from :class:`fdmm.accounting.UpdateAccountant`:

* `total_updates` / `total_insertions` / `total_deletions`
* `phase_rebuilds` — how many times the :math:`z`-system was rebuilt from scratch
* `rematch_u_scans` / `rematch_b_scans` / `rematch_a_scans` — number of vertices scanned during local-search rematching
* `greedy_rebuilds` — fallbacks to full greedy reconstruction of :math:`M^*`
* `stale_cleanups` — edges removed from :math:`M^*` because they were deleted from the graph

These counters are **not** a proof of the amortised bound; they are empirical
bookkeeping to help debug where time is spent.

## Benchmark Execution

```bash
python benchmarks/bench_fdmm.py --n 200 --mode basic --updates 5000
```

Output includes elapsed time, updates per second, and rebuild counts.

## Fidelity Report

| Component | Status | Notes |
|---|---|---|
| Dynamic graph layer | **APPROXIMATE** | Adjacency sets (BST → Python ``set`` noted). |
| :math:`z`-subgraph system definition | **EXACT** | All invariants implemented and testable. |
| :math:`z`-system construction Step 1 | **EXACT** | Greedy maximal :math:`M` with degree cap :math:`z`; A/B/U derived from :math:`M`. |
| :math:`z`-system construction Step 2 | **APPROXIMATE** | P1-fixing reconstruction; exact edge-switching rule inside :math:`B` is UNKNOWN. |
| Multi-level structure | **APPROXIMATE** | Levels rebuilt independently; recursive derivation reconstructed. |
| Edge colouring (Thm 2.4) | **UNKNOWN** | Vizing :math:`O(m\Delta)` instead of ABB+26 :math:`O(m^{1+o(1)})`. |
| Phase management | **APPROXIMATE** | Phase lengths reconstructed from parameter table. |
| Rebuilding :math:`M^*` | **APPROXIMATE** | Greedy construction instead of paper's :math:`\tilde O(m+n)`. |
| Rematching :math:`A` scan limit | **EXACT** | Fixed to :math:`2\tau+1 = 64r/z+1` per paper. |
| Rematching :math:`U` / :math:`B` | **APPROXIMATE** | Reconstructed from English descriptions; scans are bounded by list sizes. |
| Maximality verification | **EXACT** | Brute-force settled-vertex check. |
| Accounting / counters | **EXACT** | Explicit counters present; no theorem claims made. |

### Known Mismatches

1. **Adjacency BSTs** → Python ``set`` (asymptotics preserved, constants differ).
2. **Edge colouring** — standard Vizing recolouring with backtracking fallback
   for dense graphs. Correct but slower than ABB+26.
3. **Rebuild of :math:`M`** — Step 2 uses a best-effort reconstruction because
   the exact switching rule is truncated.
4. **Multi-level rebuild** — levels rebuilt independently for clarity.
5. **Rematching pseudocode** — reconstructed from descriptions; exact constants
   in :math:`O(r/z)` bounds not specified in excerpt.
6. **Subphases** — not implemented; only full-phase rebuilds are used.

## Optional Extensions

These are **not** part of the baseline reproduction and are isolated from it:

| Extension | Status | Label |
|---|---|---|
| Adjacency BSTs | Not implemented | engineering-only improvement |
| ABB+26 edge colouring | Not implemented | explicitly out of scope |
| Incremental :math:`M^*` | Not implemented | reasonable future extension |
| Exact phase constants | Not implemented | explicitly out of scope (unknown) |
| Subphase augmentation | Not implemented | explicitly out of scope (unknown) |
| Batch updates | Not implemented | reasonable future extension |
| Visualisation of subgraph system | Not implemented | engineering-only improvement |
| Multiprocessing | Not implemented | engineering-only improvement |

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/xyz`).
3. Run tests and type checks (`pytest`, `mypy fdmm/`).
4. Submit a pull request.

## License

MIT
