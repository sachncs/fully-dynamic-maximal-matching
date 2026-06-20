# Architecture Overview

This document describes the internal architecture of the FDMM implementation.

## High-Level Design

```
┌─────────────────────────────────────────────────┐
│              DynamicMaximalMatching              │
│          (main algorithm entry point)            │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐  ┌──────────────────────┐     │
│  │   Dynamic    │  │   ZSubgraphSystem    │     │
│  │    Graph     │  │  (A, B, U, M, Λ, L) │     │
│  └──────┬──────┘  └──────────┬───────────┘     │
│         │                    │                   │
│  ┌──────┴──────┐  ┌─────────┴──────────┐       │
│  │  Matching   │  │  Edge Colouring     │       │
│  │  (greedy)   │  │  (Vizing's theorem) │       │
│  └─────────────┘  └────────────────────┘       │
│                                                 │
│  ┌─────────────┐  ┌────────────────────┐       │
│  │  Updates    │  │    Accounting      │       │
│  │ (insert/    │  │  (update counters) │       │
│  │  delete)    │  │                    │       │
│  └─────────────┘  └────────────────────┘       │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Module Responsibilities

### `graph.py` — Dynamic Graph

The foundation layer. Maintains an undirected graph with O(1) edge queries and degree lookups using adjacency sets.

- **Data structure**: `dict[int, set[int]]` adjacency representation
- **Complexity**: O(1) amortised for add/remove/query (Python `set` instead of BST)

### `matching.py` — Greedy Matching

Provides the greedy maximal matching construction used during rebuilds.

- `greedy_maximal_matching(graph, degree_cap)` — builds a maximal matching with optional degree cap
- `partner_of(matching, vertex)` — O(1) lookup of a vertex's partner
- `build_partner_map(matching)` — builds a full partner map from a matching set

### `edge_coloring.py` — Vizing Edge Colouring

Deterministic (Δ+1)-edge-colouring via Vizing's algorithm with exponential backtracking fallback.

- **Input**: graph G, maximum degree Δ
- **Output**: proper edge colouring using at most Δ+1 colours
- **Complexity**: O(mΔ) worst case (paper requires O(m<sup>1+o(1)</sup>), which is out of scope)

### `z_system.py` — Z-Subgraph System

The core combinatorial structure from the paper. A `ZSubgraphSystem` partitions vertices into:

| Set | Description |
|-----|-------------|
| **A** | High-degree vertices (matched in M) |
| **B** | Medium-degree vertices |
| **U** | Low-degree / unmatched vertices |
| **S** | A ∪ B (settled vertices) |
| **M** | Degree-constrained edge subset |

Additional data:
- **Λ(u)** for u ∈ U: neighbours of u in B ∪ U
- **L(a)** for a ∈ A: neighbours of a in U

Invariants enforced:
- **P1**: |N_G(u) ∩ B| ≤ 2z for all u ∈ U
- **P2**: Each a ∈ A is matched only to vertices in S
- **Degree bounds**: all vertices have degree ≤ z in M

### `dynamic_matching.py` — Main Algorithm

The `DynamicMaximalMatching` class orchestrates:

1. **Initialisation**: builds the initial z-subgraph system
2. **Phase management**: triggers rebuilds after every r updates
3. **Insertion handling**: adds edge and repairs the matching
4. **Deletion handling**: removes edge and rematches affected vertices
5. **Rebuild**: reconstructs the z-system from scratch

Two modes:
- **Basic**: single-level z-system with z = ⌊n<sup>2/3</sup>⌋, r = ⌊n<sup>4/3</sup>⌋
- **Multi-level**: k-level recursive system with k = Θ(log n)

### `updates.py` — Update Handlers

Implements the vertex-level repair procedures:

- `rematch_u(algo, u)` — rematch an unmatched U-vertex by scanning Λ(u)
- `rematch_b(algo, b)` — rematch a B-vertex via the auxiliary graph H
- `rematch_a(algo, a)` — rematch an A-vertex by scanning L(a)
- `handle_insertion(algo, u, v)` — process an edge insertion
- `handle_deletion(algo, u, v)` — process an edge deletion

### `invariants.py` — Invariant Checks

Standalone verification functions:

- `check_maximal_matching(graph, matching)` — brute-force maximality check
- `check_z_system_invariants(system)` — verifies all z-system properties
- `check_multi_level_i3(mls)` — multi-level invariant I3

### `accounting.py` — Update Counters

The `UpdateAccountant` class tracks empirical costs:

- Insertion/deletion counts
- Phase rebuild counts
- Scan sizes for each vertex type (U, B, A)
- Greedy rebuild and stale cleanup counts

### `simulation.py` — Replay Utilities

- `random_update_sequence(n, m, rng)` — generates random insert/delete sequences
- `replay_updates(algo, updates)` — replays a sequence against an algorithm instance

### `cli.py` — Command-Line Interface

Entry point for `fdmm` command. Runs a demo with random updates and prints statistics.

## Data Flow

### Insert Edge (u, v)

```
insert_edge(u, v)
  ├── graph.add_edge(u, v)
  ├── if in M*: do nothing
  ├── else:
  │   ├── if u ∈ U: rematch_u(u)
  │   ├── if v ∈ U: rematch_v(v)
  │   ├── if both in B: try H-based rematch
  │   └── fallback: rebuild
  └── accountant.record_insertion()
```

### Delete Edge (u, v)

```
delete_edge(u, v)
  ├── graph.remove_edge(u, v)
  ├── if (u,v) ∈ M*: M*.remove(u,v)
  ├── rematch affected vertices
  └── accountant.record_deletion()
```

### Phase Rebuild

```
rebuild()
  ├── rebuild z-system from scratch
  ├── rebuild M* from M_1
  ├── rebuild auxiliary graph H
  └── accountant.record_rebuild()
```

## Known Approximations

| Component | Paper | Implementation |
|-----------|-------|----------------|
| Adjacency structure | BSTs (O(log n)) | Python sets (O(1) amortised) |
| Edge colouring | ABB+26 O(m<sup>1+o(1)</sup>) | Vizing O(mΔ) |
| Multi-level rebuild | Recursive derivation | Independent level rebuilds |
| Rematching scans | Bounded by O(r/z) | Unbounded scans |
| M* maintenance | Incremental | Greedy reconstruction |
| Subphases | Implemented | Not implemented |
