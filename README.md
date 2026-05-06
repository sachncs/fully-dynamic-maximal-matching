# FDMM — Fully Dynamic Maximal Matching

[![CI](https://github.com/placeholder/fdmm/actions/workflows/ci.yml/badge.svg)](https://github.com/placeholder/fdmm/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/placeholder/fdmm/branch/main/graph/badge.svg)](https://codecov.io/gh/placeholder/fdmm)
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

### API

#### `DynamicMaximalMatching(n, mode="basic")`

* `insert_edge(u, v)` — insert an undirected edge and repair the matching.
* `delete_edge(u, v)` — delete an undirected edge and repair the matching.
* `get_matching()` — return a copy of the current maximal matching.
* `is_maximal()` — verify that the current matching is maximal.
* `matching_size()` — number of edges in the matching.
* `statistics()` — runtime statistics (n, m, matching size, updates, etc.).

## Running Tests

```bash
pytest tests/ -v
```

All tests verify that the maintained matching is maximal after every
operation.

## Project Structure

```
fdmm/
├── pyproject.toml
├── README.md
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── fdmm/
│   ├── __init__.py
│   ├── types.py              # Type aliases and helpers
│   ├── graph.py              # DynamicGraph
│   ├── edge_coloring.py      # Vizing edge colouring
│   ├── z_system.py           # ZSubgraphSystem + MultiLevelSystem
│   └── dynamic_matching.py   # Main algorithm
├── tests/
│   └── test_fdmm.py          # Comprehensive unit tests
├── scripts/
│   └── demo.py               # Runnable demo
└── docs/
    └── index.md              # API documentation
```

## Fidelity Report

| Component | Status | Notes |
|---|---|---|
| Dynamic graph layer | **Exact** | Adjacency sets (BST → Python ``set`` noted). |
| :math:`z`-subgraph system | **Exact** | All invariants implemented and testable. |
| Multi-level structure | **Approximate** | Levels rebuilt independently; recursive derivation reconstructed. |
| Edge colouring (Thm 2.4) | **Approximate** | Vizing :math:`O(m\Delta)` instead of ABB+26 :math:`O(m^{1+o(1)})`. |
| Phase management | **Approximate** | Phase lengths reconstructed from parameter table. |
| Rebuilding :math:`M` | **Approximate** | Greedy construction instead of paper's :math:`\tilde O(m+n)`. |
| Rematching | **Approximate** | Reconstructed from English descriptions; stale-list safety nets added. |
| Maximality verification | **Exact** | Brute-force settled-vertex check. |

### Known Mismatches

1. **Adjacency BSTs** → Python ``set`` (asymptotics preserved, constants differ).
2. **Edge colouring** — standard Vizing recolouring with backtracking fallback
   for dense graphs. Correct but slower than ABB+26.
3. **Rebuild of :math:`M`** — greedy degree-constrained construction.
4. **Multi-level rebuild** — levels rebuilt independently for clarity.
5. **Rematching pseudocode** — reconstructed from descriptions; exact constants
   in :math:`O(r/z)` bounds not specified in excerpt.

## Extensions (Optional)

These are **not** part of the baseline reproduction:

* **Adjacency BSTs** — replace ``set`` with a balanced BST for strict
  :math:`O(\log n)` operations.
* **ABB+26 edge colouring** — integrate a true almost-linear-time algorithm
  when available.
* **Incremental :math:`M^*`** — maintain the matching incrementally without
  greedy recomputation.
* **Exact phase constants** — enforce exact :math:`O(r/z)` scan limits once
  the paper's pseudocode is available.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/xyz`).
3. Run tests and type checks (`pytest`, `mypy fdmm/`).
4. Submit a pull request.

## License

MIT
