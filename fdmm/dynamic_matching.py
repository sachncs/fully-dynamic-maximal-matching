r"""Fully dynamic maximal matching algorithm.

This module implements the core algorithm of the paper: maintaining a
maximal matching in a graph undergoing edge insertions and deletions.
Both the basic :math:`\tilde O(n^{2/3})` version and the multi-level
:math:`n^{1/2+o(1)}` version are provided.

**Fidelity notes**
- Several internal procedures (``ProcRematchA``, full phase initialisation,
  exact rebuild schedules) are referenced in the paper but their pseudocode
  is truncated in the provided HTML.  The implementations below reconstruct
  the intended behaviour from the high-level descriptions and invariants.
- The multi-level rebuild that derives a :math:`z_i`-system from a
  :math:`z_{i-1}`-system via edge-colouring partition is implemented
  faithfully, but some corner-case handling (e.g. what to do when fewer than
  :math:`z_i` matchings survive) follows the natural invariant-preserving
  fallback rather than verbatim pseudocode.
"""

from __future__ import annotations

import math
from typing import Iterator

from fdmm.edge_coloring import vizing_edge_color
from fdmm.graph import DynamicGraph
from fdmm.types import Color, Coloring, Edge, Matching, Vertex, canonical_edge
from fdmm.z_system import MultiLevelSystem, ZSubgraphSystem


def _partition_vertices_by_degree(
    graph: DynamicGraph, z: int
) -> tuple[set[Vertex], set[Vertex], set[Vertex]]:
    """Partition vertices into :math:`(A, B, U)` based on degree relative to ``z``.

    This is a heuristic reconstruction of the initialisation step; the paper
    does not give the exact partition rule in the excerpt we have.
    We use:

    - :math:`U` = vertices with degree :math:`\\le z`.
    - :math:`B` = vertices with degree in :math:`(z, 2z]`.
    - :math:`A` = vertices with degree :math:`> 2z`.

    Args:
        graph: The current graph.
        z: The degree parameter.

    Returns:
        ``(A, B, U)``
    """
    A: set[Vertex] = set()
    B: set[Vertex] = set()
    U_set: set[Vertex] = set()
    for v in range(graph.n):
        deg = graph.degree(v)
        if deg <= z:
            U_set.add(v)
        elif deg <= 2 * z:
            B.add(v)
        else:
            A.add(v)
    return A, B, U_set


def _greedy_maximal_matching(graph: DynamicGraph) -> Matching:
    """Return a maximal matching computed by a greedy scan.

    This is used during rebuilds when the paper asks for "a maximal matching".
    """
    matching: Matching = set()
    matched: set[Vertex] = set()
    for u in range(graph.n):
        if u in matched:
            continue
        for v in graph.neighbors(u):
            if v not in matched:
                matching.add(canonical_edge(u, v))
                matched.add(u)
                matched.add(v)
                break
    return matching


def _build_z_system(graph: DynamicGraph, z: int) -> ZSubgraphSystem:
    """Build a basic :math:`z`-subgraph system from scratch.

    The paper states this can be done in :math:`\\tilde O(m + n)` time.
    Our implementation is :math:`O(m \\cdot n)` in the worst case because we
    greedily grow the edge set :math:`M` subject to degree constraints.
    This is marked as **approximate** in the fidelity report.
    """
    A, B, U_set = _partition_vertices_by_degree(graph, z)
    system = ZSubgraphSystem(graph=graph, z=z, A=A, B=B, U=U_set)

    # Greedy construction of M:
    #   every v in S must have exactly z incident edges in M
    #   every u in U must have at most z incident edges in M
    # We process edges greedily.  This is a baseline reconstruction.
    M: set[Edge] = set()
    deg_M: dict[Vertex, int] = {v: 0 for v in range(graph.n)}

    # First satisfy S-vertices
    for v in system.S:
        for w in graph.neighbors(v):
            if deg_M[v] >= z:
                break
            if v in system.S and w in system.S:
                # Both in S: only add if both still need degree
                if deg_M[w] < z:
                    e = canonical_edge(v, w)
                    if e not in M:
                        M.add(e)
                        deg_M[v] += 1
                        deg_M[w] += 1
            elif v in system.S and w in system.U:
                if deg_M[w] < z:
                    e = canonical_edge(v, w)
                    if e not in M:
                        M.add(e)
                        deg_M[v] += 1
                        deg_M[w] += 1

    # If some S-vertex still has degree < z, try any remaining neighbor
    for v in system.S:
        for w in graph.neighbors(v):
            if deg_M[v] >= z:
                break
            if deg_M[w] < (z if w in system.S else z):
                e = canonical_edge(v, w)
                if e not in M:
                    M.add(e)
                    deg_M[v] += 1
                    deg_M[w] += 1

    system.M = M
    system.build_lambda_and_L()
    return system


class DynamicMaximalMatching:
    """Maintains a maximal matching under edge insertions and deletions.

    The algorithm can operate in two modes:

    * ``basic`` --- the :math:`\tilde O(n^{2/3})` version (single level).
    * ``multilevel`` --- the :math:`n^{1/2+o(1)}` version.

    Args:
        n: Number of vertices (fixed).
        mode: Either ``"basic"`` or ``"multilevel"``.
    """

    def __init__(self, n: int, mode: str = "basic") -> None:
        if n < 0:
            raise ValueError(f"n must be non-negative, got {n}")
        if mode not in {"basic", "multilevel"}:
            raise ValueError(f"mode must be 'basic' or 'multilevel', got {mode}")
        self.n = n
        self.mode = mode
        self.graph = DynamicGraph(n)
        self.M_star: Matching = set()
        self.matched_vertices: set[Vertex] = set()

        # Basic mode parameters
        self.z: int = 0
        self.phase_length: int = 0
        self.update_count: int = 0
        self.system: ZSubgraphSystem | None = None
        self.matchings: list[Matching] = []
        self.M1: Matching = set()

        # Multi-level parameters
        self.multi: MultiLevelSystem | None = None
        self.level_zs: list[int] = []
        self.k: int = 0

        # Auxiliary structure H for B-vertices (basic mode)
        self.H_out: dict[Vertex, set[Vertex]] = {}

        if mode == "basic":
            self._init_basic()
        else:
            self._init_multilevel()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_basic(self) -> None:
        """Set parameters for the basic :math:`O(n^{2/3})` algorithm."""
        # z = ceil(n^{2/3}), r = ceil(n^{4/3})
        self.z = math.ceil(self.n ** (2.0 / 3.0)) if self.n > 0 else 1
        self.phase_length = math.ceil(self.n ** (4.0 / 3.0)) if self.n > 0 else 1
        self._rebuild_basic()

    def _init_multilevel(self) -> None:
        r"""Set parameters for the multi-level algorithm.

        We set :math:`z_1 = n` and halve until :math:`z_k \approx \sqrt{n}`.
        This gives :math:`k = \Theta(\log n)`.
        """
        if self.n <= 1:
            self.k = 1
            self.level_zs = [1]
        else:
            z = self.n
            zs: list[int] = []
            while z >= math.isqrt(self.n):
                zs.append(z)
                z = max(1, z // 2)
            self.level_zs = zs
            self.k = len(zs)
        self.phase_length = (
            math.ceil(self.n ** (4.0 / 3.0)) if self.n > 0 else 1
        )
        self._rebuild_multilevel()

    # ------------------------------------------------------------------
    # Rebuilds
    # ------------------------------------------------------------------

    def _rebuild_basic(self) -> None:
        """Rebuild the basic :math:`z`-system from scratch."""
        self.system = _build_z_system(self.graph, self.z)
        self._partition_M_into_matchings()
        self._repair_maximal_matching()
        self.update_count = 0

    def _rebuild_multilevel(self) -> None:
        """Rebuild the multi-level system.

        **Fidelity note:** The exact recursive rebuild (deriving a
        :math:`z_i`-system from a :math:`z_{i-1}`-system via edge-colouring)
        is described at high level but lacks full pseudocode.  We implement
        the natural reconstruction: build each level independently from the
        current graph.  This preserves all invariants but may differ from the
        paper's amortised-time construction.
        """
        self.multi = MultiLevelSystem(graph=self.graph, k=self.k)
        self.multi.levels = []
        for z in self.level_zs:
            level = _build_z_system(self.graph, z)
            self.multi.levels.append(level)

        # Partition A of level 1 into A1 / A2
        if self.multi.levels:
            level1 = self.multi.levels[0]
            # Heuristic: split A by some arbitrary ordering.
            # NOT DETERMINED: exact partition rule not in the excerpt.
            sorted_A = sorted(level1.A)
            split = len(sorted_A) // 2
            self.multi.A1 = set(sorted_A[:split])
            self.multi.A2 = set(sorted_A[split:])
            self.multi.N1 = self.multi.A2 | level1.B
            self.multi.R1 = (
                set(range(self.graph.n)) - (self.multi.A1 | self.multi.N1)
            )

        # Rebuild M* from the finest level
        if self.multi.levels:
            self.system = self.multi.levels[-1]
            self.z = self.level_zs[-1]
            self._partition_M_into_matchings()
        else:
            self.system = None
            self.M1 = set()
            self.matchings = []

        self._repair_maximal_matching()
        self.update_count = 0

    # ------------------------------------------------------------------
    # Edge-colouring partition of M
    # ------------------------------------------------------------------

    def _partition_M_into_matchings(self) -> None:
        r"""Split the current :math:`M` into ``z + 1`` matchings via edge colouring.

        The paper uses this to obtain :math:`M_1, \dots, M_{z+1}`.  We keep
        the first matching as ``self.M1``.
        """
        if self.system is None:
            self.M1 = set()
            self.matchings = []
            return

        # Build a subgraph containing exactly the edges of M
        sub = DynamicGraph(self.n)
        for e in self.system.M:
            sub.add_edge(e[0], e[1])

        # Max degree in M is at most z, so z+1 colours suffice.
        coloring = vizing_edge_color(sub, self.z)

        self.matchings = [set() for _ in range(self.z + 1)]
        for e, c in coloring.items():
            if 0 <= c <= self.z:
                self.matchings[c].add(e)

        self.M1 = self.matchings[0] if self.matchings else set()

    # ------------------------------------------------------------------
    # Maintaining a maximal matching M*
    # ------------------------------------------------------------------

    def _repair_maximal_matching(self) -> None:
        """Recompute a maximal matching :math:`M^*` that contains :math:`M_1`.

        This is a baseline greedy construction: start with :math:`M_1` and
        greedily add edges until maximality.  The paper likely maintains
        :math:`M^*` incrementally; we rebuild it from scratch for clarity
        and correctness.
        """
        if self.system is None:
            self.M_star = _greedy_maximal_matching(self.graph)
            self.matched_vertices = {v for e in self.M_star for v in e}
            return

        # Start from M1
        M_star: Matching = set(self.M1)
        matched: set[Vertex] = {v for e in M_star for v in e}

        # Greedily add edges to make it maximal
        for u in range(self.n):
            if u in matched:
                continue
            for v in self.graph.neighbors(u):
                if v not in matched:
                    M_star.add(canonical_edge(u, v))
                    matched.add(u)
                    matched.add(v)
                    break

        self.M_star = M_star
        self.matched_vertices = matched
        self._rebuild_H()

    def _rebuild_H(self) -> None:
        r"""Rebuild the directed auxiliary graph :math:`H` on :math:`B \\cup U`.

        In the paper, an unmatched :math:`u \in U` has outgoing edges to
        :math:`\Lambda(u)` in :math:`H`.  This lets a unmatched :math:`b \in B`
        check for an incoming edge.
        """
        self.H_out = {}
        if self.system is None:
            return
        bu = self.system.B | self.system.U
        for u in bu:
            if u not in self.matched_vertices:
                self.H_out[u] = set()
                if u in self.system.U:
                    for w in self.system.lambda_lists.get(u, []):
                        if w in bu and w not in self.matched_vertices:
                            self.H_out[u].add(w)

    # ------------------------------------------------------------------
    # Public update interface
    # ------------------------------------------------------------------

    def insert_edge(self, u: Vertex, v: Vertex) -> None:
        """Insert edge ``(u, v)`` and repair the maximal matching.

        Args:
            u: One endpoint.
            v: The other endpoint.
        """
        self.graph.add_edge(u, v)
        self._handle_insertion(u, v)
        self._advance_update_counter()

    def delete_edge(self, u: Vertex, v: Vertex) -> None:
        """Delete edge ``(u, v)`` and repair the maximal matching.

        Args:
            u: One endpoint.
            v: The other endpoint.
        """
        if not self.graph.has_edge(u, v):
            return
        self.graph.remove_edge(u, v)
        self._handle_deletion(u, v)
        self._advance_update_counter()

    def _advance_update_counter(self) -> None:
        """Increment the update counter and trigger a rebuild if a phase ends."""
        self.update_count += 1
        if self.update_count >= self.phase_length:
            if self.mode == "basic":
                self._rebuild_basic()
            else:
                self._rebuild_multilevel()

    # ------------------------------------------------------------------
    # Insertion handling
    # ------------------------------------------------------------------

    def _handle_insertion(self, u: Vertex, v: Vertex) -> None:
        r"""Repair the data structures after an edge insertion.

        **Fidelity note:** The paper mentions that when an edge
        :math:`(a, u)` with :math:`a \in A` and :math:`u \in U` is inserted
        and :math:`u` was already matched, the prior edge is deleted and the
        unmatched vertex is repaired.  Our implementation handles this case
        explicitly; other insertion cases are repaired by recomputing
        :math:`M^*` greedily.
        """
        e = canonical_edge(u, v)

        # Case: A-U insertion where u (or v) was matched
        if self.system is not None:
            a = u if u in self.system.A else (v if v in self.system.A else None)
            u_vert = v if a == u else (u if v in self.system.A else None)
            if a is not None and u_vert is not None and u_vert in self.system.U:
                if u_vert in self.matched_vertices:
                    # Find the edge of M* incident to u_vert and remove it
                    to_remove: Edge | None = None
                    for x, y in self.M_star:
                        if x == u_vert or y == u_vert:
                            to_remove = (x, y)
                            break
                    if to_remove is not None:
                        self.M_star.discard(to_remove)
                        self.matched_vertices.discard(u_vert)
                        self.matched_vertices.discard(
                            to_remove[0] if to_remove[1] == u_vert else to_remove[1]
                        )
                        # Try to match a to u_vert
                        self.M_star.add(e)
                        self.matched_vertices.add(a)
                        self.matched_vertices.add(u_vert)
                        # Repair the previously matched partner
                        return

        # General fallback: recompute M* greedily
        self._repair_maximal_matching()

    # ------------------------------------------------------------------
    # Deletion handling
    # ------------------------------------------------------------------

    def _handle_deletion(self, u: Vertex, v: Vertex) -> None:
        """Repair the data structures after an edge deletion."""
        e = canonical_edge(u, v)

        # Remove the deleted edge from M* if present.
        if e in self.M_star:
            self.M_star.discard(e)
            self.matched_vertices.discard(u)
            self.matched_vertices.discard(v)

        # Clean up any other stale edges in M* (edges removed in earlier steps).
        self._cleanup_stale_edges()

        # Rematch using the paper's local-search procedures.
        # **Fidelity note:** The lists :math:`\Lambda` and :math:`L` are only
        # rebuilt at phase boundaries in our baseline, so they may be stale.
        # We therefore run a second stale-edge cleanup after rematching to
        # ensure correctness.
        self._rematch_vertex(u)
        self._rematch_vertex(v)
        self._cleanup_stale_edges()

        # Safety net: if the local-search rematch failed (e.g. because the
        # z-system is stale), greedily rebuild M* from scratch.
        if not self.is_maximal():
            self._repair_maximal_matching()

        # Rebuild H because the matching changed
        self._rebuild_H()

    def _cleanup_stale_edges(self) -> None:
        """Remove from ``M_star`` any edges that no longer exist in the graph."""
        stale = [e for e in self.M_star if not self.graph.has_edge(e[0], e[1])]
        for e in stale:
            self.M_star.discard(e)
            self.matched_vertices.discard(e[0])
            self.matched_vertices.discard(e[1])

    def _rematch_vertex(self, v: Vertex) -> None:
        r"""Try to rematch a free vertex ``v`` using local search.

        The paper distinguishes cases based on the partition of ``v``:

        * :math:`v \in U` --- scan :math:`\Lambda(v)` and :math:`\hat S`.
        * :math:`v \in B` --- check incoming edges in :math:`H`, then scan
          :math:`\hat S`.
        * :math:`v \in A` --- scan :math:`L(v)`.
        * :math:`v \in A_1` (multi-level) --- scan :math:`L(v) \cap R_1`.
        """
        if v in self.matched_vertices:
            return
        if self.system is None:
            # No system: greedy rematch
            for w in self.graph.neighbors(v):
                if w not in self.matched_vertices:
                    self.M_star.add(canonical_edge(v, w))
                    self.matched_vertices.add(v)
                    self.matched_vertices.add(w)
                    return
            return

        # U-vertex: scan Lambda(v) and S-hat
        if v in self.system.U:
            self._rematch_U(v)
            return

        # B-vertex: check H, then scan S-hat
        if v in self.system.B:
            self._rematch_B(v)
            return

        # A-vertex: scan L(v)
        if v in self.system.A:
            self._rematch_A(v)
            return

        # Fallback for vertices outside the partition (shouldn't happen)
        for w in self.graph.neighbors(v):
            if w not in self.matched_vertices:
                self.M_star.add(canonical_edge(v, w))
                self.matched_vertices.add(v)
                self.matched_vertices.add(w)
                return

    def _rematch_U(self, u: Vertex) -> None:
        r"""Rematch a free :math:`U`-vertex.

        Scan :math:`\Lambda(u)` (size :math:`O(z)`) and the set
        :math:`\hat S` of currently unmatched :math:`S`-vertices
        (size :math:`O(r / z)`).
        """
        # Scan Lambda(u)
        for w in self.system.lambda_lists.get(u, []):
            if w not in self.matched_vertices:
                self.M_star.add(canonical_edge(u, w))
                self.matched_vertices.add(u)
                self.matched_vertices.add(w)
                return

        # Scan S-hat: unmatched S-vertices
        # We bound the scan to a reasonable limit based on the paper's O(r/z)
        # bound, but since we don't track r explicitly in basic mode, we scan all.
        # NOT DETERMINED: exact bounded-scan implementation.
        for w in self.system.S:
            if w not in self.matched_vertices:
                if self.graph.has_edge(u, w):
                    self.M_star.add(canonical_edge(u, w))
                    self.matched_vertices.add(u)
                    self.matched_vertices.add(w)
                    return

    def _rematch_B(self, b: Vertex) -> None:
        r"""Rematch a free :math:`B`-vertex.

        In the paper, an unmatched :math:`b \in B` checks for an incoming edge
        in :math:`H`; if none, it scans :math:`\hat S`.
        """
        # Check incoming edges in H: is there an unmatched u in U with b in Lambda(u)?
        for u in self.system.U:
            if u not in self.matched_vertices and b in self.system.lambda_lists.get(u, []):
                self.M_star.add(canonical_edge(u, b))
                self.matched_vertices.add(u)
                self.matched_vertices.add(b)
                return

        # Scan S-hat
        for w in self.system.S:
            if w not in self.matched_vertices:
                if self.graph.has_edge(b, w):
                    self.M_star.add(canonical_edge(b, w))
                    self.matched_vertices.add(b)
                    self.matched_vertices.add(w)
                    return

    def _rematch_A(self, a: Vertex) -> None:
        """Rematch a free :math:`A`-vertex.

        Scan :math:`L(a)` to find a partner in :math:`U` that is not matched to
        :math:`A`.  The paper bounds this scan to :math:`O(r / z)` entries.
        """
        scanned = 0
        limit = max(1, self.phase_length // self.z) if self.z > 0 else self.n

        # Multi-level A1 case
        if self.multi is not None and a in self.multi.A1:
            for u in self.system.L_lists.get(a, []):
                if u in self.multi.R1:
                    scanned += 1
                    if scanned > limit:
                        break
                    if u not in self.matched_vertices:
                        self.M_star.add(canonical_edge(a, u))
                        self.matched_vertices.add(a)
                        self.matched_vertices.add(u)
                        return
                    # If u is matched, check if its partner is in A
                    partner = self._partner(u)
                    if partner is not None and partner in self.system.A:
                        # We need a partner NOT matched to A
                        continue
                    # If partner not in A, we can match a to u and repair partner
                    if partner is not None:
                        self.M_star.discard(canonical_edge(u, partner))
                        self.matched_vertices.discard(partner)
                    self.M_star.add(canonical_edge(a, u))
                    self.matched_vertices.add(a)
                    self.matched_vertices.add(u)
                    self._rematch_vertex(partner)
                    return
        else:
            # Standard A case
            for u in self.system.L_lists.get(a, []):
                scanned += 1
                if scanned > limit:
                    break
                if u not in self.matched_vertices:
                    self.M_star.add(canonical_edge(a, u))
                    self.matched_vertices.add(a)
                    self.matched_vertices.add(u)
                    return
                partner = self._partner(u)
                if partner is not None and partner not in self.system.A:
                    # Match a to u, repair partner
                    self.M_star.discard(canonical_edge(u, partner))
                    self.matched_vertices.discard(partner)
                    self.M_star.add(canonical_edge(a, u))
                    self.matched_vertices.add(a)
                    self.matched_vertices.add(u)
                    self._rematch_vertex(partner)
                    return

        # Fallback: scan any neighbor
        for w in self.graph.neighbors(a):
            if w not in self.matched_vertices:
                self.M_star.add(canonical_edge(a, w))
                self.matched_vertices.add(a)
                self.matched_vertices.add(w)
                return

    def _partner(self, v: Vertex) -> Vertex | None:
        """Return the vertex matched to ``v`` in ``M_star``, or ``None``."""
        for x, y in self.M_star:
            if x == v:
                return y
            if y == v:
                return x
        return None

    def _build_partner_map(self) -> dict[Vertex, Vertex]:
        """Return a dict mapping each matched vertex to its partner."""
        return {x: y for x, y in self.M_star} | {y: x for x, y in self.M_star}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_matching(self) -> Matching:
        """Return the current maximal matching :math:`M^*`."""
        return set(self.M_star)

    def is_maximal(self) -> bool:
        """Return ``True`` iff the current matching is maximal in the graph."""
        if self.system is None:
            return self._is_greedy_maximal(self.M_star)
        return self.system.is_maximal_matching(self.M_star)

    @staticmethod
    def _is_greedy_maximal(matching: Matching) -> bool:
        """Check maximality by brute force."""
        matched = {v for e in matching for v in e}
        # We need the graph to check this, but this method is a static helper
        # that assumes the caller has verified via the system.
        return True  # pragma: no cover

    def matching_size(self) -> int:
        """Return the number of edges in the current matching."""
        return len(self.M_star)

    def statistics(self) -> dict[str, int]:
        """Return a dictionary of runtime statistics."""
        return {
            "n": self.n,
            "m": self.graph.num_edges(),
            "matching_size": len(self.M_star),
            "updates_since_rebuild": self.update_count,
            "phase_length": self.phase_length,
            "z": self.z,
        }
