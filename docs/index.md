# FDMM Documentation

## Overview

FDMM is a Python reproduction of *"A Faster Deterministic Algorithm for
Fully Dynamic Maximal Matching"* (arXiv:2605.00797v1).

## Modules

- `fdmm.graph` — Dynamic undirected graph data structure.
- `fdmm.edge_coloring` — Deterministic edge colouring (Vizing's theorem).
- `fdmm.z_system` — The :math:`z`-subgraph and multi-level systems.
- `fdmm.dynamic_matching` — Core fully-dynamic maximal matching algorithm.

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

See inline docstrings for full API documentation.
