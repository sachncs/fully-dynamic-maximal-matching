# FDMM Documentation

## Overview

FDMM is a Python reproduction of *"A Faster Deterministic Algorithm for
Fully Dynamic Maximal Matching"* (arXiv:2605.00797v1).

Repository: `https://github.com/sachn-cs/fully-dynamic-maximal-matching`

## Modules

- `fdmm.graph` — Dynamic undirected graph data structure.
- `fdmm.matching` — Greedy maximal matching and partner helpers.
- `fdmm.edge_coloring` — Deterministic edge colouring (Vizing's theorem).
- `fdmm.z_system` — The :math:`z`-subgraph system, multi-level system, and
  construction routine.
- `fdmm.dynamic_matching` — Core fully-dynamic maximal matching algorithm.
- `fdmm.updates` — Insertion, deletion, and rematch handlers.
- `fdmm.invariants` — Standalone invariant checkers.
- `fdmm.accounting` — Explicit update-work counters.
- `fdmm.simulation` — Random update generators and replay utilities.
- `fdmm.cli` — Command-line entry point.

## Quick Start

```python
from fdmm import DynamicMaximalMatching

algo = DynamicMaximalMatching(n=100, mode="basic")
algo.insert_edge(0, 1)
algo.insert_edge(2, 3)
assert algo.is_maximal()
print(algo.matching_size())
```

## API Reference

See inline docstrings for full API documentation.  Key public classes:

* :class:`fdmm.graph.DynamicGraph`
* :class:`fdmm.z_system.ZSubgraphSystem`
* :class:`fdmm.z_system.MultiLevelSystem`
* :class:`fdmm.dynamic_matching.DynamicMaximalMatching`
* :class:`fdmm.accounting.UpdateAccountant`

## Additional Documents

- `docs/paper_restatement.md` — Extracted paper content, notation, and UNKNOWNs.
- `docs/audit_report.md` — Section-by-section audit of code vs. paper.
