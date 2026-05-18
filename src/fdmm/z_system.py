r"""The :math:`z`-subgraph system and multi-level generalisation.

This module defines the combinatorial data structures that lie at the heart
of the paper's algorithm.  The implementation follows the notation and
invariants of Section 2 as closely as possible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

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
        r"""Check property (P1): :math:`|N_G(u) \cap B| \le 2z` for all :math:`u \in U`."""
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


def build_z_system(graph: DynamicGraph, z: int) -> ZSubgraphSystem:
    r"""Build a :math:`z`-subgraph system from scratch.

    This implements the two-step deterministic construction described in the
    paper.  Step 1 (greedy maximal :math:`M` with degree cap :math:`z`) is
    reproduced exactly.  Step 2 (promoting :math:`U`-vertices to :math:`B`
    and edge-switching inside :math:`B`) is reconstructed from the high-level
    description because the full pseudocode is truncated.

    **Fidelity note:** Step 2 is marked APPROXIMATE.  When a :math:`U`-vertex
    has at least :math:`z` neighbours in :math:`B` but all of those neighbours
    are already saturated in :math:`M`, we cannot perform the exact edge-switch
    without the missing switching rule, so the vertex remains in :math:`U`.
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

    # Step 2: process U-vertices to fix P1.
    # NOTE: exact switching rule inside B is NOT PROVIDED in the paper excerpt.
    # We approximate by only adding edges to B-neighbours that still have
    # spare capacity in M.  If no such neighbour exists, the vertex stays in U.
    for u in list(system.U):
        neighbors_in_B = [w for w in graph.neighbors(u) if w in system.B]
        if len(neighbors_in_B) >= z:
            added = 0
            for w in neighbors_in_B:
                if added >= z:
                    break
                if deg_M[w] < z:
                    e = canonical_edge(u, w)
                    if e not in M:
                        M.add(e)
                        deg_M[u] += 1
                        deg_M[w] += 1
                        added += 1
                # If w is saturated, exact switching rule is unknown.
            if deg_M[u] == z:
                system.U.discard(u)
                system.B.add(u)
                # If a B-vertex loses all its M-edges to U, promote it to A.
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

    system.M = M
    system.build_lambda_and_L()
    return system
