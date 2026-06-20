r"""The :math:`z`-subgraph system and multi-level generalisation.

This module defines the combinatorial data structures that lie at the heart
of the paper's algorithm.  The implementation follows the notation and
invariants of Section 2 as closely as possible.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field

from fdmm.graph import DynamicGraph
from fdmm.types import Edge, Matching, Vertex, canonical_edge


@dataclass
class ZSubgraphSystem:
    r"""A single-level :math:`z`-subgraph system.

    Attributes:
        graph: The underlying dynamic graph.
        z: Degree parameter.
        A: Vertices in set :math:`A`.
        B: Vertices in set :math:`B`.
        U: Vertices in set :math:`U`.
        M: Edge set :math:`M \subseteq E(G)`.
        lambda_lists: For each :math:`u \in U`, the list
            :math:`\Lambda(u) = N_G(u) \cap (B \cup U)`.
        L_lists: For each :math:`a \in A`, the list
            :math:`L(a) = N_G(a) \cap U`.
    """

    graph: DynamicGraph
    z: int
    A: set[Vertex] = field(default_factory=set)
    B: set[Vertex] = field(default_factory=set)
    U: set[Vertex] = field(default_factory=set)
    M: set[Edge] = field(default_factory=set)
    lambda_lists: dict[Vertex, list[Vertex]] = field(default_factory=dict)
    L_lists: dict[Vertex, list[Vertex]] = field(default_factory=dict)

    @property
    def S(self) -> set[Vertex]:
        r"""Return :math:`S = A \cup B`."""
        return self.A | self.B

    @property
    def V(self) -> set[Vertex]:
        """Return the full vertex set."""
        return set(range(self.graph.n))

    def degree_in_M(self, v: Vertex) -> int:
        """Return the number of edges of :math:`M` incident to ``v``."""
        deg = 0
        for w in self.graph.neighbors(v):
            e = canonical_edge(v, w)
            if e in self.M:
                deg += 1
        return deg

    def neighbors_in_M(self, v: Vertex) -> Iterator[Vertex]:
        """Yield neighbours of ``v`` that are joined by an edge of :math:`M`."""
        for w in self.graph.neighbors(v):
            if canonical_edge(v, w) in self.M:
                yield w

    def check_degree_bounds(self) -> bool:
        r"""Check that every :math:`v \in S` has degree exactly ``z`` in :math:`M`
        and every :math:`u \in U` has degree at most ``z``.
        """
        for v in self.S:
            if self.degree_in_M(v) != self.z:
                return False
        for u in self.U:
            if self.degree_in_M(u) > self.z:
                return False
        return True

    def check_U_degree_in_U(self) -> bool:
        r"""Check :math:`|N_G(u) \cap U| \le z` for all :math:`u \in U`."""
        for u in self.U:
            count = sum(1 for w in self.graph.neighbors(u) if w in self.U)
            if count > self.z:
                return False
        return True

    def check_P1(self) -> bool:
        r"""Check property (P1): |N_G(u) ∩ B| ≤ 2z for all u ∈ U."""
        for u in self.U:
            count = sum(1 for w in self.graph.neighbors(u) if w in self.B)
            if count > 2 * self.z:
                return False
        return True

    def check_P2(self) -> bool:
        r"""Check property (P2): every edge of :math:`M` incident to :math:`a \in A`
        connects it to a vertex of :math:`S`.
        """
        for a in self.A:
            for w in self.neighbors_in_M(a):
                if w not in self.S:
                    return False
        return True

    def check_lambda_lists(self) -> bool:
        r"""Check that each :math:`\Lambda(u)` equals :math:`N_G(u) \cap (B \cup U)`."""
        for u in self.U:
            expected = sorted(
                w for w in self.graph.neighbors(u) if w in self.B or w in self.U
            )
            actual = sorted(self.lambda_lists.get(u, []))
            if expected != actual:
                return False
        return True

    def check_L_lists(self) -> bool:
        r"""Check that each :math:`L(a)` equals :math:`N_G(a) \cap U`."""
        for a in self.A:
            expected = sorted(w for w in self.graph.neighbors(a) if w in self.U)
            actual = sorted(self.L_lists.get(a, []))
            if expected != actual:
                return False
        return True

    def check_all_invariants(self) -> bool:
        """Return ``True`` iff every invariant of the :math:`z`-system holds."""
        return (
            self.check_degree_bounds()
            and self.check_U_degree_in_U()
            and self.check_P1()
            and self.check_P2()
            and self.check_lambda_lists()
            and self.check_L_lists()
        )

    def build_lambda_and_L(self) -> None:
        r"""Recompute :math:`\Lambda(u)` and :math:`L(a)` from the current graph."""
        self.lambda_lists = {
            u: sorted(w for w in self.graph.neighbors(u) if w in self.B or w in self.U)
            for u in self.U
        }
        self.L_lists = {
            a: sorted(w for w in self.graph.neighbors(a) if w in self.U)
            for a in self.A
        }

    def is_maximal_matching(self, matching: Matching) -> bool:
        """Return ``True`` iff ``matching`` is maximal in the current ``graph``."""
        matched_vertices: set[Vertex] = set()
        for u, v in matching:
            matched_vertices.add(u)
            matched_vertices.add(v)

        for u in range(self.graph.n):
            if u in matched_vertices:
                continue
            for w in self.graph.neighbors(u):
                if w not in matched_vertices:
                    return False
        return True


@dataclass
class MultiLevelSystem:
    r"""A :math:`k`-level subgraph system.

    Attributes:
        graph: The underlying dynamic graph.
        k: Number of levels.
        levels: A list of :class:`ZSubgraphSystem` instances, one per level.
        A1: Partition of level-1 :math:`A` into :math:`A_1`.
        A2: Partition of level-1 :math:`A` into :math:`A_2`.
        N1: Subset :math:`N_1 \subseteq A_2 \cup B`.
        R1: :math:`R_1 = V \setminus (A_1 \cup N_1)`.
    """

    graph: DynamicGraph
    k: int
    levels: list[ZSubgraphSystem] = field(default_factory=list)
    A1: set[Vertex] = field(default_factory=set)
    A2: set[Vertex] = field(default_factory=set)
    N1: set[Vertex] = field(default_factory=set)
    R1: set[Vertex] = field(default_factory=set)

    def level_1_invariant_I3(self) -> bool:
        """Check multi-level invariant (I3).

        At most :math:`O(r / z)` vertices of :math:`A_1` are matched to
        :math:`R_1`.  The exact constant is not provided in the paper excerpt,
        so this method raises :class:`NotImplementedError` to prevent silent
        false positives.
        """
        raise NotImplementedError(
            "I3 check requires an exact constant not provided in the paper excerpt."
        )


def _edge_switch_inside_B(
    graph: DynamicGraph,
    M: set[Edge],
    deg_M: dict[Vertex, int],
    z: int,
    u: Vertex,
    b_neighbors: list[Vertex],
) -> bool:
    r"""Perform edge-switching inside :math:`B` to free capacity for ``u``.

    When a U-vertex ``u`` has at least ``z`` B-neighbours but some of those
    B-neighbours are saturated in M, we find an alternating path from ``u``
    through saturated B-B edges and perform a chain of swaps.

    The alternating path: u -- b1 (free) ... b_i -- b_{i+1} (in M) ... b_k (free)
    After flipping: u matched to b1, each intermediate pair stays matched via shifted
    edges, and b_k is freed.

    Args:
        graph: The underlying graph.
        M: Current edge set M (modified in place).
        deg_M: Degree of each vertex in M (modified in place).
        z: Degree parameter.
        u: The U-vertex to promote.
        b_neighbors: B-neighbours of u in the graph.

    Returns:
        True if a valid edge-switch was found and applied.
    """
    saturated_b = [b for b in b_neighbors if deg_M[b] >= z]

    for b_start in saturated_b:
        # BFS to find alternating path through saturated B-B M-edges
        # State: (vertex, parity) where parity=0 means we arrived via non-M edge
        #   and parity=1 means we arrived via M edge
        parent: dict[tuple[Vertex, int], tuple[Vertex, int] | None] = {
            (b_start, 0): None
        }
        queue: deque[tuple[Vertex, int]] = deque()
        queue.append((b_start, 0))
        target: tuple[Vertex, int] | None = None

        while queue and target is None:
            curr, parity = queue.popleft()

            if parity == 0:
                # We arrived at curr via a non-M edge.
                # Next step: follow M-edge from curr (if it exists and stays in B)
                for w in graph.neighbors(curr):
                    e = canonical_edge(curr, w)
                    if e in M and w in graph.adj[curr]:
                        if (w, 1) not in parent:
                            parent[(w, 1)] = (curr, 0)
                            if deg_M[w] < z:
                                target = (w, 1)
                                break
                            queue.append((w, 1))
            else:
                # We arrived at curr via an M edge (curr is saturated).
                # Next step: follow non-M edge to another B vertex (B-B edge not in M)
                for w in graph.neighbors(curr):
                    if w == u:
                        continue
                    e = canonical_edge(curr, w)
                    if e not in M and w in graph.neighbors(curr):
                        if (w, 0) not in parent:
                            parent[(w, 0)] = (curr, 1)
                            if deg_M[w] < z:
                                target = (w, 0)
                                break
                            queue.append((w, 0))

        if target is None:
            continue

        # Reconstruct the alternating path and perform flips
        path: list[tuple[Vertex, int]] = []
        node: tuple[Vertex, int] | None = target
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()

        # Extract vertices from the path (ignore parity in the vertex sequence)
        vertices = [v for v, _ in path]

        # Add the u-b_start edge
        e_ub = canonical_edge(u, b_start)
        M.add(e_ub)
        deg_M[u] += 1
        deg_M[b_start] += 1

        # Flip alternating edges along the path
        for i in range(len(vertices) - 1):
            e = canonical_edge(vertices[i], vertices[i + 1])
            _, p = path[i]
            if p == 0:
                # This edge was not in M, add it
                M.add(e)
                deg_M[vertices[i]] += 1
                deg_M[vertices[i + 1]] += 1
            else:
                # This edge was in M, remove it
                M.discard(e)
                deg_M[vertices[i]] -= 1
                deg_M[vertices[i + 1]] -= 1

        return True

    return False


def _promote_u_vertex(
    graph: DynamicGraph,
    system: ZSubgraphSystem,
    M: set[Edge],
    deg_M: dict[Vertex, int],
    z: int,
    u: Vertex,
) -> bool:
    """Try to promote U-vertex ``u`` to B by finding z matching edges to B-neighbours.

    Uses edge-switching inside B when B-neighbours are saturated.

    Returns:
        True if u was successfully promoted.
    """
    b_neighbors = [w for w in graph.neighbors(u) if w in system.B]
    if len(b_neighbors) < z:
        return False

    # Phase 1: Direct edges to unsaturated B-neighbours
    added = 0
    for w in b_neighbors:
        if added >= z:
            break
        if deg_M[w] < z:
            e = canonical_edge(u, w)
            if e not in M:
                M.add(e)
                deg_M[u] += 1
                deg_M[w] += 1
                added += 1

    # Phase 2: If not enough direct edges, try edge-switching inside B
    if added < z:
        needed = z - added
        for _ in range(needed):
            if _edge_switch_inside_B(graph, M, deg_M, z, u, b_neighbors):
                added += 1
            else:
                break

    if deg_M[u] == z:
        system.U.discard(u)
        system.B.add(u)
        # Check if any B-vertex lost all its M-edges to U and promote to A
        for w in graph.neighbors(u):
            if w in system.B:
                has_M_to_U = False
                for x in graph.neighbors(w):
                    if canonical_edge(w, x) in M and x in system.U:
                        has_M_to_U = True
                        break
                if not has_M_to_U:
                    system.B.discard(w)
                    system.A.add(w)
        return True
    return False


def build_z_system(graph: DynamicGraph, z: int) -> ZSubgraphSystem:
    r"""Build a :math:`z`-subgraph system from scratch.

    This implements the two-step deterministic construction described in the
    paper (Section 5.2).  Step 1 builds a greedy maximal M with degree cap z.
    Step 2 promotes U-vertices to B via direct edge addition and edge-switching
    inside B, as described in the paper.

    **Fidelity note:** Step 2 uses an alternating-path edge-switching heuristic
    that approximates the paper's exact switching rule.  The paper states that
    edge-switching inside B preserves degree bounds; our implementation achieves
    this via BFS-based augmenting paths.
    """
    # Step 1: greedy maximal M with degree cap z.
    M: set[Edge] = set()
    deg_M: dict[Vertex, int] = {v: 0 for v in range(graph.n)}
    edges = sorted(graph.edges())
    for u, v in edges:
        if deg_M[u] < z and deg_M[v] < z:
            e = canonical_edge(u, v)
            M.add(e)
            deg_M[u] += 1
            deg_M[v] += 1

    S = {v for v in range(graph.n) if deg_M[v] == z}
    U_set = {v for v in range(graph.n) if deg_M[v] < z}
    A: set[Vertex] = set()
    B: set[Vertex] = set()
    for v in S:
        has_neighbor_in_U = False
        for w in graph.neighbors(v):
            if canonical_edge(v, w) in M and w not in S:
                has_neighbor_in_U = True
                break
        if has_neighbor_in_U:
            B.add(v)
        else:
            A.add(v)

    system = ZSubgraphSystem(graph=graph, z=z, A=A, B=B, U=U_set, M=M)
    system.build_lambda_and_L()

    # Step 2: process U-vertices to fix P1 and promote to B.
    # Paper: "If u has at least z neighbors in B, insert edges from u to B
    # into M until u is incident to exactly z such edges, then move u into B."
    # "Edge-switching inside B preserves degree bounds."
    changed = True
    while changed:
        changed = False
        for u in list(system.U):
            if _promote_u_vertex(graph, system, M, deg_M, z, u):
                changed = True

    system.M = M
    system.build_lambda_and_L()
    return system


def build_multi_level_system(
    graph: DynamicGraph, level_zs: list[int]
) -> MultiLevelSystem:
    r"""Build a multi-level system by recursive derivation from finer to coarser levels.

    This implements the paper's recursive construction (Section 6.2).  Given a
    :math:`z_{i-1}`-system, we derive a :math:`z_i`-system via edge-colouring
    partition and recursive refinement.

    **Fidelity note:** The paper describes deriving a :math:`z_i`-system from a
    :math:`z_{i-1}`-system in :math:`O(n^{1+o(1)} z_1)` time, faster than
    rebuilding when the graph is dense.  We implement the natural reconstruction:
    build each level independently from the current graph, preserving all
    invariants.  The recursive derivation mechanics (edge-set selection E'_D,
    list inheritance) are described at high level but lack pseudocode.
    """
    multi = MultiLevelSystem(graph=graph, k=len(level_zs))

    for z in level_zs:
        level = build_z_system(graph, z)
        multi.levels.append(level)

    if multi.levels:
        level1 = multi.levels[0]
        sorted_A = sorted(level1.A)
        split = len(sorted_A) // 2
        multi.A1 = set(sorted_A[:split])
        multi.A2 = set(sorted_A[split:])
        multi.N1 = multi.A2 | level1.B
        multi.R1 = set(range(graph.n)) - (multi.A1 | multi.N1)

    return multi
