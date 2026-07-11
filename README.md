# FDMM — Fully Dynamic Maximal Matching

[![CI](https://github.com/sachn-cs/fully-dynamic-maximal-matching/actions/workflows/ci.yml/badge.svg)](https://github.com/sachn-cs/fully-dynamic-maximal-matching/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sachn-cs/fully-dynamic-maximal-matching/branch/master/graph/badge.svg)](https://codecov.io/gh/sachn-cs/fully-dynamic-maximal-matching)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Python reproduction of *"A Faster Deterministic Algorithm for Fully Dynamic
> Maximal Matching"* (arXiv:2605.00797v1, Chuzhoy–Khanna–Song, STOC 2026).

A deterministic algorithm that maintains a **maximal matching** in an undirected graph under online edge insertions and deletions, achieving amortised update time *n*<sup>1/2+o(1)</sup>.

---

## Features

- **Basic mode** — *Õ*(*n*<sup>2/3</sup>) amortised update time (single-level *z*-subgraph system)
- **Multi-level mode** — *n*<sup>1/2+o(1)</sup> amortised update time (recursive *k*-level system with *k* = Θ(log *n*))
- Deterministic (Δ+1)-edge-colouring (Vizing's theorem)
- Comprehensive invariant checks and maximality verification
- Explicit update-work counters for empirical cost auditing
- Simulation utilities for random update sequences and replay
- Zero runtime dependencies — pure Python
- Full type annotations with `mypy` strict mode

## Installation

Requires **Python ≥ 3.10**.

```bash
git clone https://github.com/sachn-cs/fully-dynamic-maximal-matching.git
cd fully-dynamic-maximal-matching
pip install -e ".[dev]"
```

For an isolated environment:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
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

### Command-Line Interface

Run the built-in demo:

```bash
fdmm --n 20 --mode basic --updates 200
fdmm --n 50 --mode multilevel --updates 500
```

Or use the demo script directly:

```bash
python scripts/demo.py --n 20 --mode basic --updates 200
```

### API Reference

#### `DynamicMaximalMatching(n, mode="basic")`

| Method | Description |
|--------|-------------|
| `insert_edge(u, v)` | Insert an undirected edge and repair the matching |
| `delete_edge(u, v)` | Delete an undirected edge and repair the matching |
| `get_matching()` | Return a copy of the current maximal matching |
| `is_maximal()` | Verify that the current matching is maximal |
| `matching_size()` | Number of edges in the matching |
| `partner(v)` | Return the partner of vertex `v` in the matching, or `None` |
| `statistics()` | Runtime statistics (n, m, matching size, update counters, etc.) |
| `augment_m1_at_subphase_boundary()` | Augment `M_1` at the next subphase boundary |
| `try_augment_m1(start, matched_in_m1)` | BFS for an `M_1` augmenting path starting at `start` |
| `flip_augmenting_path(path)` | Flip edges along an augmenting path |

#### Construction primitives (`fdmm.z_system`)

| Function | Description |
|----------|-------------|
| `build_z_system(graph, z)` | Build a fresh `ZSubgraphSystem` from a graph |
| `build_multi_level_system(graph, level_zs)` | Stack `z`-systems for the recursive algorithm |
| `edge_switch_inside_B(...)` | Alternating-path capacity recovery inside `B` |
| `promote_u_vertex(...)` | Try to promote a `U`-vertex into `B` |

#### Edge colouring (`fdmm.edge_coloring`)

| Function | Description |
|----------|-------------|
| `abb_edge_color(graph, delta)` | Degree-ordered greedy `(Δ+1)`-colouring |
| `vizing_edge_color(graph, delta)` | Classical Vizing recolouring with backtracking fallback |
| `color_single_edge`, `alternating_path`, `flip_path` | Building-block primitives |

### Simulation & Replay

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

### Interpreting Update Counters

`statistics()` includes counters from `UpdateAccountant`:

| Counter | Description |
|---------|-------------|
| `total_updates` | Total number of insert/delete operations |
| `total_insertions` | Number of edge insertions |
| `total_deletions` | Number of edge deletions |
| `phase_rebuilds` | Times the *z*-system was rebuilt from scratch |
| `rematch_u_scans` | Vertices scanned during U-rematching |
| `rematch_b_scans` | Vertices scanned during B-rematching |
| `rematch_a_scans` | Vertices scanned during A-rematching |
| `greedy_rebuilds` | Fallbacks to full greedy reconstruction of M* |
| `stale_cleanups` | Edges removed from M* because they were deleted |

> These counters are **not** a proof of the amortised bound; they are empirical bookkeeping to help debug where time is spent.

## Project Structure

```
fdmm/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── .gitignore
├── .editorconfig
├── .gitattributes
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
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
│   └── test_fdmm.py              # Comprehensive unit tests
├── benchmarks/
│   └── bench_fdmm.py             # Lightweight throughput benchmark
├── scripts/
│   └── demo.py                   # Runnable demo
├── examples/
│   ├── example_basic.py
│   └── example_multilevel.py
└── docs/
    ├── index.md                  # API documentation
    ├── getting-started.md        # Getting started guide
    ├── architecture.md           # Architecture overview
    ├── faq.md                    # Frequently asked questions
    ├── paper_restatement.md      # Parsed paper content + UNKNOWNs
    └── audit_report.md           # Codebase vs. paper audit
```

## Running Tests

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest --cov=fdmm --cov-report=term-missing tests/
```

All tests verify that the maintained matching is maximal after every operation. Invariant checks are included for the *z*-subgraph system.

## Benchmarks

```bash
python benchmarks/bench_fdmm.py --n 200 --mode basic --updates 5000
```

Output includes elapsed time, updates per second, and rebuild counts.

## Fidelity Report

| Component | Status | Notes |
|-----------|--------|-------|
| Dynamic graph layer | **APPROXIMATE** | Adjacency sets (BST → Python `set` noted) |
| *z*-subgraph system definition | **EXACT** | All invariants implemented and testable |
| *z*-system construction Step 1 | **EXACT** | Greedy maximal M with degree cap *z*; A/B/U derived from M |
| *z*-system construction Step 2 | **APPROXIMATE** | P1-fixing reconstruction; exact edge-switching rule inside B is UNKNOWN |
| Multi-level structure | **APPROXIMATE** | Levels rebuilt independently; recursive derivation reconstructed |
| Edge colouring (Thm 2.4) | **UNKNOWN** | Vizing O(mΔ) instead of ABB+26 O(m<sup>1+o(1)</sup>) |
| Phase management | **APPROXIMATE** | Phase lengths reconstructed from parameter table |
| Rebuilding M* | **APPROXIMATE** | Greedy construction instead of paper's Õ(m+n) |
| Rematching A scan limit | **EXACT** | Fixed to 2τ+1 = 64r/z+1 per paper |
| Rematching U / B | **APPROXIMATE** | Reconstructed from English descriptions; scans bounded by list sizes |
| Maximality verification | **EXACT** | Brute-force settled-vertex check |
| Accounting / counters | **EXACT** | Explicit counters present; no theorem claims made |

### Known Mismatches

1. **Adjacency BSTs** → Python `set` (asymptotics preserved, constants differ)
2. **Edge colouring** — standard Vizing recolouring with backtracking fallback for dense graphs. Correct but slower than ABB+26
3. **Rebuild of M** — Step 2 uses a best-effort reconstruction because the exact switching rule is truncated
4. **Multi-level rebuild** — levels rebuilt independently for clarity
5. **Rematching pseudocode** — reconstructed from descriptions; exact constants in O(r/z) bounds not specified in excerpt
6. **Subphases** — not implemented; only full-phase rebuilds are used

## Optional Extensions

These are **not** part of the baseline reproduction and are isolated from it:

| Extension | Status | Label |
|-----------|--------|-------|
| Adjacency BSTs | Not implemented | engineering-only improvement |
| ABB+26 edge colouring | Not implemented | explicitly out of scope |
| Incremental M* | Not implemented | reasonable future extension |
| Exact phase constants | Not implemented | explicitly out of scope (unknown) |
| Subphase augmentation | Not implemented | explicitly out of scope (unknown) |
| Batch updates | Not implemented | reasonable future extension |
| Visualisation of subgraph system | Not implemented | engineering-only improvement |
| Multiprocessing | Not implemented | engineering-only improvement |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Build system | setuptools (pyproject.toml) |
| Testing | pytest, pytest-cov, hypothesis |
| Type checking | mypy (strict mode) |
| Linting | ruff |
| CI | GitHub Actions |

## Roadmap

- [ ] Fix edge-switching rule inside B (Step 2 construction)
- [ ] Implement ABB+26 deterministic edge colouring
- [ ] Add subphase management
- [ ] Implement incremental M* maintenance
- [ ] Add recursive multi-level rebuild derivation
- [ ] Visualisation of subgraph system
- [ ] Benchmarking suite with automated regression detection

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Security

To report security vulnerabilities, please see our [Security Policy](SECURITY.md).

## License

This project is licensed under the [MIT License](LICENSE).

---

*Based on "A Faster Deterministic Algorithm for Fully Dynamic Maximal Matching" by Julia Chuzhoy, Sanjeev Khanna, and Junkai Song (arXiv:2605.00797v1).*
