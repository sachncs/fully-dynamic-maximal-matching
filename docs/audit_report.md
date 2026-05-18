# Audit Report: Existing Codebase vs. Paper

## Method

Each component of the existing `fdmm/` implementation is compared against the paper text. Status: **EXACT**, **APPROXIMATE**, or **UNKNOWN**.

---

## Component-by-Component Audit

### `fdmm.graph.DynamicGraph`

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Undirected graph, $n$ fixed | EXACT | `DynamicGraph.__init__` fixes $n$. |
| Adjacency lists as BSTs for $O(\log n)$ ops | APPROXIMATE | Code uses Python `set` (amortized $O(1)$). Asymptotics preserved, constants differ. Fidelity note already present. |
| Edge insertion / deletion | EXACT | `add_edge`, `remove_edge` correctly update adjacency and count. |
| Self-loop handling | EXACT | Paper model excludes self-loops; code silently ignores them. |

**Verdict:** APPROXIMATE (adjacency structure).

---

### `fdmm.edge_coloring.vizing_edge_color`

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Theorem 2.4: deterministic $(\Delta+1)$-edge-colouring in $O(m^{1+o(1)})$ | UNKNOWN | Code implements standard Vizing recolouring ($O(m\Delta)$) plus exponential backtracking fallback. Correct but asymptotically slower. Fidelity note present. |
| Proper colouring guaranteed | EXACT | Vizing + backtrack guarantee correctness. |

**Verdict:** UNKNOWN (algorithm differs; correctness preserved).

---

### `fdmm.z_system.ZSubgraphSystem`

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Attributes: $A, B, U, M, \Lambda(u), L(a)$ | EXACT | Dataclass fields match. |
| Property $S=A\cup B$ | EXACT | `@property def S` correct. |
| Degree bounds in $M$ | EXACT | `check_degree_bounds` matches paper. |
| $U$-$U$ degree bound | EXACT | `check_U_degree_in_U` matches. |
| P1: $|N_G(u)\cap B|\le 2z$ | EXACT | `check_P1` matches. |
| P2: $a\in A$ matched only to $S$ | EXACT | `check_P2` matches. |
| $\Lambda(u)=N_G(u)\cap(B\cup U)$ | EXACT | `check_lambda_lists` matches. |
| $L(a)=N_G(a)\cap U$ | EXACT | `check_L_lists` matches. |
| `build_lambda_and_L` recomputation | EXACT | Rebuilds from current graph. |
| `is_maximal_matching` brute-force | EXACT | Checks settled-vertex condition. |
| Construction (two-step algorithm) | UNKNOWN | Code uses `_build_z_system` with greedy degree-constrained edge selection. Does **not** implement Step 2 (promoting $U$ to $B$, edge-switching inside $B$). Paper's $\tilde O(n+m)$ construction not reproduced. |

**Verdict:** UNKNOWN (construction missing Step 2).

---

### `fdmm.z_system.MultiLevelSystem`

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| $k$ levels, $z_1>...>z_k$ | APPROXIMATE | Levels built independently from graph, not recursively derived from previous level. High-level description only. |
| $A_1, A_2, N_1, R_1$ | APPROXIMATE | Split is arbitrary sorted partition (50/50). Paper's exact rule unspecified. |
| Invariant I3 | UNKNOWN | `level_1_invariant_I3` vacuously returns `True`. No real check. |

**Verdict:** APPROXIMATE / UNKNOWN.

---

### `fdmm.dynamic_matching.DynamicMaximalMatching`

#### Parameters

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Basic: $z=\lfloor n^{2/3}\rfloor$, $r=\lfloor n^{4/3}\rfloor$ | EXACT | `_init_basic` computes these correctly. |
| Multi-level: $z_1=n$, halve until $\approx\sqrt n$ | EXACT | `_init_multilevel` computes sequence correctly. |
| Phase length $r$ | EXACT | Used as rebuild threshold. |

#### Rebuilds

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Rebuild $z$-system from scratch at phase start | EXACT | `_rebuild_basic` calls `_build_z_system`. |
| Rebuild multi-level recursively | UNKNOWN | Code rebuilds each level independently. Paper's recursive derivation via $E'_D$ and edge-colouring partition not implemented. |
| Partition $M$ into $z+1$ matchings via edge-colouring | APPROXIMATE | Uses Vizing instead of ABB+26. Correct number of classes. |
| Recompute $M^*$ from $M_1$ | APPROXIMATE | Greedy extension. Paper likely maintains incrementally; no pseudocode provided. |

#### Insertion Handling

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Observation 2.3-based repair | UNKNOWN | Code has a single A-U case then falls back to greedy rebuild. Paper does not give insertion-specific local-search pseudocode. |

#### Deletion Handling

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Remove deleted edge from $M^*$ | EXACT | `_handle_deletion` does this. |
| Rematch endpoints | APPROXIMATE | `_rematch_vertex` dispatches by partition, but `_rematch_U`, `_rematch_B`, `_rematch_A` are reconstructions from English descriptions. |
| Rematching $U$ scan $\Lambda(u)$ and $\hat S$ | APPROXIMATE | Scans `lambda_lists` then scans all $S$ (no bound). Paper says size $O(r/z)$; code does not bound scan. |
| Rematching $B$ via $H$ | APPROXIMATE | `_rematch_B` checks all $U$ for incoming edge instead of using $H$ in-neighbour set. Then scans $\hat S$ unboundedly. |
| Rematching $A$ scan first $2\tau+1$ entries of $L(a)$ | APPROXIMATE | `_rematch_A` uses `limit = max(1, phase_length // z)` which equals $r/z$ (not $2\tau+1 = 64r/z+1$). This is a mismatch. Also the A1 multi-level case uses `multi.R1` but the limit and scan logic differ from paper. |
| Subphase boundary augmentation | UNKNOWN | Not implemented. Code only uses phase-level rebuilds. |

#### Auxiliary Graph $H$

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Directed $H$ on $B\cup U$ with outgoing edges from unmatched $U$ to $\Lambda(u)$ | APPROXIMATE | `_rebuild_H` builds a dict-of-sets. Does not support $O(\log n)$ BST operations. Update logic on status changes not integrated into rematch procedures. |

#### Accounting / Amortized Analysis

| Paper Requirement | Code Status | Notes |
|-------------------|-------------|-------|
| Explicit work counters | MISSING | No module tracks update work, scan sizes, or phase costs. |
| Amortized bound claims | NOT CLAIMED | Code does not claim any theorem. Good. |

**Verdict:** Mixed. Parameter choices are EXACT. Rebuild and repair are APPROXIMATE / UNKNOWN.

---

## Global Issues Found

1. **Leading underscores** — `_build_z_system`, `_partition_M_into_matchings`, `_repair_maximal_matching`, `_rematch_vertex`, etc. The user instruction says "Do not use semi-private names." The existing code uses many leading-underscore helpers. These need renaming or inlining.
2. **Missing accounting module** — no explicit counters for update work.
3. **No subphase management** — paper has subphases; code only has phases.
4. **No `simulation.py`** — no replay engine for update sequences.
5. **No `invariants.py`** — invariant checks are embedded in `z_system.py`.
6. **Tests** — existing tests cover graph, colouring, basic dynamism, but do not test:
   - phase/level transitions explicitly,
   - invariant preservation after every update,
   - edge-case graphs (e.g., empty, single vertex, complete),
   - randomized sequences for multi-level,
   - regression cases for repair logic.

---

## Summary Table

| Component | Status |
|-----------|--------|
| Dynamic graph | APPROXIMATE |
| Edge colouring | UNKNOWN |
| $z$-system definition / checks | EXACT |
| $z$-system construction | UNKNOWN |
| Multi-level system | APPROXIMATE / UNKNOWN |
| Parameter choices | EXACT |
| Phase management | APPROXIMATE (missing subphases) |
| Rebuild of $M^*$ | APPROXIMATE |
| Insertion handling | UNKNOWN |
| Deletion handling (U, B, A rematch) | APPROXIMATE |
| Auxiliary graph $H$ | APPROXIMATE |
| Accounting / counters | MISSING |
| Tests | PARTIAL |
| CLI / demo | EXISTENT |
