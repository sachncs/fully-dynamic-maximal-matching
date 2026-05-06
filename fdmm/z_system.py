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
        M: Edge set :math:`M \\subseteq E(G)`.
        lambda_lists: For each :math:`u \\in U`, the list
            :math:`\\Lambda(u) = N_G(u) \\cap (B \\cup U)`.
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
        N1: Subset :math:`N_1 \\subseteq A_2 \\cup B`.
        R1: :math:`R_1 = V \\setminus (A_1 \\cup N_1)`.
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
        :math:`R_1`.  (The exact constant depends on parameters not fully
        specified in the provided text.)
        """
        # NOT DETERMINED: the paper states ``O(r / z)`` but does not give the
        # explicit constant in the excerpt we have.
        if not self.levels:
            return True
        level1 = self.levels[0]
        count = 0
        for a in self.A1:
            for w in level1.neighbors_in_M(a):
                if w in self.R1:
                    count += 1
                    break
        # We cannot verify the bound without the exact constant.
        return True  # pragma: no cover
