r"""Fully dynamic maximal matching algorithm.

This module implements the core algorithm of the paper: maintaining a
maximal matching in a graph undergoing edge insertions and deletions.
Both the basic :math:`\tilde O(n^{2/3})` version and the multi-level
:math:`n^{1/2+o(1)}` version are provided.

Responsibilities:
    * Own the live :class:`fdmm.graph.DynamicGraph` and the maintained
      maximal matching :math:`M^*`.
    * Keep an up-to-date :math:`z`-system (or :math:`k`-level system) and
      the auxiliary directed graph :math:`H`.
    * Dispatch each update through the procedure-specific handlers in
      :mod:`fdmm.updates`.
    * Surface a small query / statistics API for callers and tests.

Algorithm sketch:

    The algorithm decomposes the vertex set into :math:`A, B, U` where
    :math:`S = A \cup B` is the set of vertices that are saturated in
    :math:`M` (degree exactly ``z`` in :math:`M`) and ``U`` is the rest.
    A first colour class of an edge-colouring of :math:`M` is used as a
    "seed" matching :math:`M_1`; greedily extending :math:`M_1` to a
    maximal matching in :math:`G` gives the reported :math:`M^*`.
    Updates are handled locally by scanning the cached lists
    :math:`\Lambda(u)` and :math:`L(a)` (of size :math:`O(z)` for the
    basic algorithm), with a full rebuild after every
    ``phase_length = n^{4/3}`` updates to amortise the rebuild cost.

**Fidelity notes**
- Several internal procedures (``ProcRematchA``, full phase initialisation,
  exact rebuild schedules) are referenced in the paper but their pseudocode
  is truncated in the provided HTML.  The implementations below reconstruct
  the intended behaviour from the high-level descriptions and invariants.
- The multi-level rebuild that derives a :math:`z_i`-system from a
  :math:`z_{i-1}`-system via edge-colouring partition is implemented
  faithfully at high level, but some corner-case handling follows the
  natural invariant-preserving fallback rather than verbatim pseudocode.

Thread-safety:
    Each ``DynamicMaximalMatching`` instance is intended to be used from
    a single thread.  Concurrent updates on the same instance are not
    supported.
"""

from __future__ import annotations

import math

from fdmm.accounting import UpdateAccountant
from fdmm.edge_coloring import abb_edge_color
from fdmm.graph import DynamicGraph
from fdmm.invariants import check_maximal_matching
from fdmm.matching import greedy_maximal_matching, partner_of
from fdmm.types import Matching, Vertex, canonical_edge
from fdmm.updates import handle_deletion, handle_insertion
from fdmm.z_system import MultiLevelSystem, ZSubgraphSystem, build_z_system


class DynamicMaximalMatching:
    r"""Maintains a maximal matching under edge insertions and deletions.

    The algorithm can operate in two modes:

    * ``"basic"`` --- the :math:`\tilde O(n^{2/3})` version (single level).
    * ``"multilevel"`` --- the :math:`n^{1/2+o(1)}` version with
      :math:`k = \Theta(\log n)` levels.

    The instance is stateful: every :meth:`insert_edge` and
    :meth:`delete_edge` mutates ``self.graph`` and ``self.M_star`` and
    may trigger a full rebuild of the supporting :math:`z`-system.  Use
    :meth:`statistics` to inspect the amortised cost.

    Attributes:
        n: Number of vertices (fixed).
        mode: ``"basic"`` or ``"multilevel"``.
        graph: The underlying :class:`DynamicGraph`.
        M_star: The maintained maximal matching.
        matched_vertices: Convenience cache of vertices incident to
            some edge of ``M_star``; kept in sync with ``M_star``.
        z: Degree parameter of the active :math:`z`-system.
        phase_length: Number of updates between full rebuilds.
        subphase_length: Number of updates between lightweight :math:`M_1`
            augmentations.
        update_count: Number of updates since the last full rebuild.
        subphase_count: Number of subphase augmentations performed.
        system: Active :math:`z`-system, or ``None``.
        matchings: Colour classes of the most recent edge-colouring of
            ``system.M`` (only ``z + 1`` of them, indexed ``0 .. z``).
        M1: First colour class, kept as the seed for :math:`M^*`.
        multi: Multi-level system, present in ``"multilevel"`` mode.
        level_zs: Per-level :math:`z` values in decreasing order.
        k: Number of levels in ``multi``.
        H_out: Outgoing arcs of the directed auxiliary graph :math:`H`.
        accountant: Bookkeeping counters from :class:`UpdateAccountant`.

    Args:
        n: Number of vertices (fixed for the lifetime of the instance).
        mode: Either ``"basic"`` or ``"multilevel"``.

    Raises:
        ValueError: If ``n`` is negative or ``mode`` is unknown.

    Example:
        >>> algo = DynamicMaximalMatching(n=10, mode="basic")
        >>> algo.insert_edge(0, 1)
        >>> algo.insert_edge(2, 3)
        >>> algo.is_maximal()
        True
        >>> sorted(algo.get_matching())
        [(0, 1), (2, 3)]
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
        self.subphase_length: int = 0
        self.update_count: int = 0
        self.subphase_count: int = 0
        self.system: ZSubgraphSystem | None = None
        self.matchings: list[Matching] = []
        self.M1: Matching = set()

        # Multi-level parameters
        self.multi: MultiLevelSystem | None = None
        self.level_zs: list[int] = []
        self.k: int = 0

        # Auxiliary structure H for B-vertices (basic mode)
        self.H_out: dict[Vertex, set[Vertex]] = {}

        # Explicit work counters (not part of the paper's algorithm)
        self.accountant = UpdateAccountant()

        if mode == "basic":
            self.init_basic()
        else:
            self.init_multilevel()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init_basic(self) -> None:
        """Set parameters for the basic :math:`\tilde O(n^{2/3})` algorithm.

        The defaults are
        :math:`z = \\lceil n^{2/3} \rceil`, :math:`r = \\lceil n^{4/3} \rceil`,
        and ``subphase_length = r // z``.
        """
        self.z = math.ceil(self.n ** (2.0 / 3.0)) if self.n > 0 else 1
        self.phase_length = math.ceil(self.n ** (4.0 / 3.0)) if self.n > 0 else 1
        self.subphase_length = max(1, self.phase_length // self.z)
        self.rebuild_basic()

    def init_multilevel(self) -> None:
        r"""Set parameters for the multi-level algorithm.

        We set :math:`z_1 = n` and halve until :math:`z_k \approx \sqrt{n}`.
        This gives :math:`k = \Theta(\log n)` as prescribed by the paper.

        The phase length and subphase length are reused from the basic
        schedule so that amortisation analysis transfers unchanged.
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
        self.subphase_length = max(1, self.phase_length // self.z) if self.z > 0 else 1
        self.rebuild_multilevel()

    # ------------------------------------------------------------------
    # Rebuilds
    # ------------------------------------------------------------------

    def rebuild_basic(self) -> None:
        """Rebuild the basic :math:`z`-system from scratch.

        Re-runs :func:`fdmm.z_system.build_z_system`, partitions the
        resulting :math:`M`, rebuilds :math:`M^*`, and resets the
        update counters.  This is an ``O(n + m)`` operation in the
        amortised budget of the algorithm.
        """
        self.system = build_z_system(self.graph, self.z)
        self.partition_m_into_matchings()
        self.rebuild_m_star_incremental()
        self.update_count = 0
        self.subphase_count = 0
        if self.accountant is not None:
            self.accountant.record_phase_rebuild()

    def rebuild_multilevel(self) -> None:
        """Rebuild the multi-level system.

        Recreates every level from the current graph and re-partitions
        the finest level.  This is more expensive than a basic rebuild
        but is amortised over ``phase_length`` updates.
        """
        self.multi = MultiLevelSystem(graph=self.graph, k=self.k)
        self.multi.levels = []
        for z in self.level_zs:
            level = build_z_system(self.graph, z)
            self.multi.levels.append(level)

        if self.multi.levels:
            level1 = self.multi.levels[0]
            sorted_A = sorted(level1.A)
            split = len(sorted_A) // 2
            self.multi.A1 = set(sorted_A[:split])
            self.multi.A2 = set(sorted_A[split:])
            self.multi.N1 = self.multi.A2 | level1.B
            self.multi.R1 = (
                set(range(self.graph.n)) - (self.multi.A1 | self.multi.N1)
            )

        if self.multi.levels:
            # Use the coarsest level for the matching partition; its
            # smaller ``z`` keeps ``z + 1`` small and so bounds the
            # number of colour classes produced.
            self.system = self.multi.levels[-1]
            self.z = self.level_zs[-1]
            self.subphase_length = max(1, self.phase_length // self.z)
            self.partition_m_into_matchings()
        else:
            self.system = None
            self.M1 = set()
            self.matchings = []

        self.rebuild_m_star_incremental()
        self.update_count = 0
        self.subphase_count = 0
        if self.accountant is not None:
            self.accountant.record_phase_rebuild()

    # ------------------------------------------------------------------
    # Edge-colouring partition of M
    # ------------------------------------------------------------------

    def partition_m_into_matchings(self) -> None:
        r"""Split the current :math:`M` into ``z + 1`` matchings via edge colouring.

        The paper uses this to obtain :math:`M_1, \dots, M_{z+1}`.  We keep
        the first matching as ``self.M1``.

        Raises:
            RuntimeError: If the colouring routine returns a colour
                outside ``[0, z]``.  This guards against silent data
                corruption if the underlying colouring implementation
                changes.
        """
        if self.system is None:
            self.M1 = set()
            self.matchings = []
            return

        sub = DynamicGraph(self.n)
        for e in self.system.M:
            sub.add_edge(e[0], e[1])

        # Use the fast ABB approximation for edge colouring
        coloring = abb_edge_color(sub, self.z)

        self.matchings = [set() for _ in range(self.z + 1)]
        dropped = 0
        for e, c in coloring.items():
            if 0 <= c <= self.z:
                self.matchings[c].add(e)
            else:
                dropped += 1
        if dropped:
            raise RuntimeError(
                f"partition_m_into_matchings: {dropped} edge(s) received "
                f"out-of-range color (expected 0..{self.z})."
            )

        self.M1 = self.matchings[0] if self.matchings else set()

    # ------------------------------------------------------------------
    # Maintaining a maximal matching M*
    # ------------------------------------------------------------------

    def rebuild_m_star_incremental(self) -> None:
        r"""Rebuild :math:`M^*` starting from :math:`M_1` and extending greedily.

        This is the paper's approach: start with :math:`M_1` (the first
        colour class from edge-colouring) and extend to a maximal
        matching by greedily adding edges to unmatched vertices.  The
        resulting matching contains :math:`M_1` and is therefore a
        valid witness for the paper's amortisation argument.

        Complexity:
            :math:`O(n + m)` in the worst case.
        """
        if self.system is None:
            self.M_star = greedy_maximal_matching(self.graph)
            self.matched_vertices = {v for e in self.M_star for v in e}
            if self.accountant is not None:
                self.accountant.record_greedy_rebuild(self.n)
            return

        M_star: Matching = set(self.M1)
        matched: set[Vertex] = {v for e in M_star for v in e}

        # Extend M1 greedily to a maximal matching
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
        self.rebuild_h()

    def repair_maximal_matching(self) -> None:
        """Recompute a maximal matching :math:`M^*` that contains :math:`M_1`.

        This is a baseline greedy construction: start with :math:`M_1` and
        greedily add edges until maximality.  The paper likely maintains
        :math:`M^*` incrementally; we rebuild it from scratch for clarity
        and correctness.

        Called when local repair in :mod:`fdmm.updates` cannot restore
        maximality.
        """
        self.rebuild_m_star_incremental()

    def rebuild_h(self) -> None:
        r"""Rebuild the directed auxiliary graph :math:`H` on :math:`B \cup U`.

        In the paper, an unmatched :math:`u \in U` has outgoing edges to
        :math:`\Lambda(u)` in :math:`H`.  This lets an unmatched
        :math:`b \in B` cheaply check for an incoming edge and either
        add it directly or recurse into a rematch.

        Only unmatched vertices are included so that :math:`H` has size
        bounded by the number of free vertices.

        Complexity:
            :math:`O(\sum_{u \in U} |\Lambda(u)|) \le O(m)`.
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
    # Subphase management
    # ------------------------------------------------------------------

    def check_subphase_boundary(self) -> bool:
        r"""Trigger subphase maintenance of :math:`M_1` when due.

        Paper Section 6.1: "Divide each phase into subphases of
        :math:`\lfloor r / z \rfloor` updates.  At subphase boundaries,
        augment :math:`M_1` using augmenting paths in :math:`M_i \cup M_1`."

        Returns:
            ``True`` iff a subphase rebuild was triggered by this call.
        """
        if self.update_count > 0 and self.update_count % self.subphase_length == 0:
            self.subphase_count += 1
            self.augment_m1_at_subphase_boundary()
            if self.accountant is not None:
                self.accountant.record_subphase_rebuild()
            return True
        return False

    def augment_m1_at_subphase_boundary(self) -> None:
        r"""Augment :math:`M_1` at a subphase boundary.

        Paper: "augment :math:`M_1` using augmenting paths in
        :math:`M_i \cup M_1` for an appropriate :math:`M_i` that still
        leaves few S-vertices unmatched."

        We find short augmenting paths to restore the :math:`M_1`
        matching quality without paying for a full rebuild.

        Complexity:
            Bounded by the number of unmatched S-vertices times the
            local BFS depth.
        """
        if self.system is None or not self.matchings:
            return

        # Find unmatched S-vertices and try to augment M_1
        matched_in_m1: set[Vertex] = set()
        for u, v in self.M1:
            matched_in_m1.add(u)
            matched_in_m1.add(v)

        # For each unmatched S-vertex, try to find an alternating path
        # that starts and ends at unmatched vertices
        for s in self.system.S:
            if s not in matched_in_m1:
                # Try to find an alternating path to augment M_1
                self.try_augment_m1(s, matched_in_m1)

    def try_augment_m1(
        self, start: Vertex, matched_in_m1: set[Vertex]
    ) -> bool:
        r"""Try to find an augmenting path for :math:`M_1` starting from ``start``.

        Uses BFS in the symmetric difference of :math:`M_1` and the
        remaining colour classes, alternating between edges in
        :math:`M_1` (entered via ``via_m1 == True``) and edges not in
        :math:`M_1` (entered via ``via_m1 == False``).  When the search
        reaches an unmatched vertex we flip the path to grow :math:`M_1`.

        Args:
            start: Unmatched vertex where the search originates.
            matched_in_m1: Set of vertices currently matched in
                :math:`M_1` (used as the termination condition).

        Returns:
            ``True`` iff an augmenting path was found and flipped.
        """
        # Simple BFS augmenting path search (limited depth for efficiency)
        from collections import deque

        # State: (vertex, is_matched_edge) where is_matched_edge indicates
        # whether we arrived via an M_1 edge or not
        visited: set[tuple[Vertex, bool]] = {(start, False)}
        queue: deque[tuple[Vertex, bool, list[Vertex]]] = deque()
        queue.append((start, False, [start]))

        while queue:
            curr, via_m1, path = queue.popleft()

            for w in self.graph.neighbors(curr):
                e = canonical_edge(curr, w)
                is_m1 = e in self.M1

                if via_m1 and not is_m1:
                    # We arrived via M_1, now take a non-M_1 edge
                    if (w, True) not in visited:
                        new_path = path + [w]
                        if w not in matched_in_m1:
                            # Found augmenting path - flip it
                            self.flip_augmenting_path(new_path)
                            return True
                        visited.add((w, True))
                        queue.append((w, True, new_path))
                elif not via_m1 and is_m1:
                    # We arrived via non-M_1, now take an M_1 edge
                    if (w, False) not in visited:
                        visited.add((w, False))
                        queue.append((w, False, path + [w]))

        return False

    def flip_augmenting_path(self, path: list[Vertex]) -> None:
        """Flip edges along an augmenting path to grow :math:`M_1`.

        Alternating paths start and end at unmatched vertices, so every
        even-indexed edge is absent from :math:`M_1` and every odd-
        indexed edge (0-based) is present; flipping inverts this and
        gains one matching edge overall.
        """
        for i in range(0, len(path) - 1, 2):
            e = canonical_edge(path[i], path[i + 1])
            if e in self.M1:
                self.M1.discard(e)
            else:
                self.M1.add(e)

    # ------------------------------------------------------------------
    # Public update interface
    # ------------------------------------------------------------------

    def insert_edge(self, u: Vertex, v: Vertex) -> None:
        """Insert edge ``(u, v)`` and repair the maximal matching.

        The edge is first added to the underlying graph; the matching is
        repaired by :func:`fdmm.updates.handle_insertion`, which knows
        about the special ``A-U`` case from Observation 2.3 of the paper.

        Args:
            u: One endpoint.
            v: The other endpoint.
        """
        self.graph.add_edge(u, v)
        handle_insertion(self, u, v)
        self.advance_update_counter()

    def delete_edge(self, u: Vertex, v: Vertex) -> None:
        """Delete edge ``(u, v)`` and repair the maximal matching.

        Deleting an edge that does not exist is a no-op (still counted as
        a deletion for accounting).  Otherwise the matching is repaired by
        :func:`fdmm.updates.handle_deletion`.

        Args:
            u: One endpoint.
            v: The other endpoint.
        """
        if not self.graph.has_edge(u, v):
            if self.accountant is not None:
                self.accountant.record_deletion()
            return
        self.graph.remove_edge(u, v)
        handle_deletion(self, u, v)
        self.advance_update_counter()

    def advance_update_counter(self) -> None:
        """Increment the update counter and trigger rebuilds as needed.

        Both the subphase boundary and the phase boundary are checked.
        The phase boundary triggers a full rebuild of the :math:`z`-system
        (or all levels, in multilevel mode).
        """
        self.update_count += 1

        # Check subphase boundary
        self.check_subphase_boundary()

        # Check phase boundary (full rebuild)
        if self.update_count >= self.phase_length:
            if self.mode == "basic":
                self.rebuild_basic()
            else:
                self.rebuild_multilevel()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_matching(self) -> Matching:
        """Return a copy of the current maximal matching :math:`M^*`.

        The returned set is detached from the algorithm's internal state,
        so the caller may mutate it without affecting future updates.

        Complexity:
            :math:`O(|M^*|)` to copy.
        """
        return set(self.M_star)

    def is_maximal(self) -> bool:
        """Return ``True`` iff the current matching is maximal in the graph.

        Uses the standalone checker in :mod:`fdmm.invariants`.

        Complexity:
            :math:`O(n + m)`.
        """
        return check_maximal_matching(self.graph, self.M_star)

    def matching_size(self) -> int:
        """Return the number of edges in the current matching."""
        return len(self.M_star)

    def partner(self, v: Vertex) -> Vertex | None:
        """Return the vertex matched to ``v`` in :math:`M^*`, or ``None``.

        Args:
            v: The vertex to look up.

        Returns:
            ``v``'s partner in :math:`M^*`, or ``None`` if ``v`` is
            unmatched.

        Complexity:
            :math:`O(|M^*|)`.  Use :meth:`build_partner_map` for repeated
            lookups.
        """
        return partner_of(self.M_star, v)

    def build_partner_map(self) -> dict[Vertex, Vertex]:
        """Return a dict mapping each matched vertex to its partner.

        Complexity:
            :math:`O(|M^*|)` time and space.
        """
        return {x: y for x, y in self.M_star} | {y: x for x, y in self.M_star}

    def statistics(self) -> dict[str, int]:
        """Return a dictionary of runtime statistics.

        Always-present keys:
            * ``n`` -- vertex count,
            * ``m`` -- current edge count,
            * ``matching_size`` -- :math:`|M^*|`,
            * ``updates_since_rebuild`` -- since the last full rebuild,
            * ``phase_length`` / ``subphase_length`` -- schedule,
            * ``subphase_count`` -- subphase repairs performed,
            * ``z`` -- current degree parameter.

        If a non-``None`` :class:`UpdateAccountant` is attached, every
        counter from :meth:`UpdateAccountant.snapshot` is merged in.

        Returns:
            A flat ``dict[str, int]`` suitable for logging or CSV export.
        """
        stats: dict[str, int] = {
            "n": self.n,
            "m": self.graph.num_edges(),
            "matching_size": len(self.M_star),
            "updates_since_rebuild": self.update_count,
            "phase_length": self.phase_length,
            "subphase_length": self.subphase_length,
            "subphase_count": self.subphase_count,
            "z": self.z,
        }
        if self.accountant is not None:
            stats.update(self.accountant.snapshot())
        return stats
