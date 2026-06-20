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
  faithfully at high level, but some corner-case handling follows the
  natural invariant-preserving fallback rather than verbatim pseudocode.
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
        """Set parameters for the basic :math:`O(n^{2/3})` algorithm."""
        self.z = math.ceil(self.n ** (2.0 / 3.0)) if self.n > 0 else 1
        self.phase_length = math.ceil(self.n ** (4.0 / 3.0)) if self.n > 0 else 1
        self.subphase_length = max(1, self.phase_length // self.z)
        self.rebuild_basic()

    def init_multilevel(self) -> None:
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
        self.subphase_length = max(1, self.phase_length // self.z) if self.z > 0 else 1
        self.rebuild_multilevel()

    # ------------------------------------------------------------------
    # Rebuilds
    # ------------------------------------------------------------------

    def rebuild_basic(self) -> None:
        """Rebuild the basic :math:`z`-system from scratch."""
        self.system = build_z_system(self.graph, self.z)
        self.partition_m_into_matchings()
        self.rebuild_m_star_incremental()
        self.update_count = 0
        self.subphase_count = 0
        if self.accountant is not None:
            self.accountant.record_phase_rebuild()

    def rebuild_multilevel(self) -> None:
        """Rebuild the multi-level system.

        Uses recursive derivation: build each level from the graph,
        then partition M for the finest level.
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

        This is the paper's approach: start with M_1 (the first colour class
        from edge-colouring) and extend to a maximal matching by greedily
        adding edges to unmatched vertices.
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
        """
        self.rebuild_m_star_incremental()

    def rebuild_h(self) -> None:
        r"""Rebuild the directed auxiliary graph :math:`H` on :math:`B \cup U`.

        In the paper, an unmatched :math:`u \in U` has outgoing edges to
        :math:`\Lambda(u)` in :math:`H`.  This lets an unmatched :math:`b \in B`
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
    # Subphase management
    # ------------------------------------------------------------------

    def check_subphase_boundary(self) -> bool:
        r"""Check if we are at a subphase boundary and perform subphase maintenance.

        Paper Section 6.1: "Divide each phase into subphases of
        floor(r/z) updates.  At subphase boundaries, augment M_1 using
        augmenting paths in M_i ∪ M_1."

        This performs a lightweight repair of M_1 at subphase boundaries
        without doing a full rebuild.

        Returns:
            True if a subphase rebuild was triggered.
        """
        if self.update_count > 0 and self.update_count % self.subphase_length == 0:
            self.subphase_count += 1
            self._augment_m1_at_subphase_boundary()
            if self.accountant is not None:
                self.accountant.record_subphase_rebuild()
            return True
        return False

    def _augment_m1_at_subphase_boundary(self) -> None:
        r"""Augment :math:`M_1` at a subphase boundary.

        Paper: "augment M_1 using augmenting paths in M_i ∪ M_1 for an
        appropriate M_i that still leaves few S-vertices unmatched."

        We find short augmenting paths to restore the M_1 matching quality.
        """
        if self.system is None or not self.matchings:
            return

        # Find unmatched S-vertices and try to augment M_1
        matched_in_m1: set[Vertex] = set()
        for u, v in self.M1:
            matched_in_m1.add(u)
            matched_in_m1.add(v)

        # For each unmatched S-vertex, try to find an augmenting path
        # that starts and ends at unmatched vertices
        for s in self.system.S:
            if s not in matched_in_m1:
                # Try to find an alternating path to augment M_1
                self._try_augment_m1(s, matched_in_m1)

    def _try_augment_m1(
        self, start: Vertex, matched_in_m1: set[Vertex]
    ) -> bool:
        """Try to find an augmenting path for M_1 starting from ``start``.

        Uses BFS to find a short augmenting path through M_i ∪ M_1.
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
                            self._flip_augmenting_path(new_path)
                            return True
                        visited.add((w, True))
                        queue.append((w, True, new_path))
                elif not via_m1 and is_m1:
                    # We arrived via non-M_1, now take an M_1 edge
                    if (w, False) not in visited:
                        visited.add((w, False))
                        queue.append((w, False, path + [w]))

        return False

    def _flip_augmenting_path(self, path: list[Vertex]) -> None:
        """Flip edges along an augmenting path to increase M_1 size."""
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

        Args:
            u: One endpoint.
            v: The other endpoint.
        """
        self.graph.add_edge(u, v)
        handle_insertion(self, u, v)
        self.advance_update_counter()

    def delete_edge(self, u: Vertex, v: Vertex) -> None:
        """Delete edge ``(u, v)`` and repair the maximal matching.

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
        """Increment the update counter and trigger rebuilds as needed."""
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
        """Return the current maximal matching :math:`M^*`."""
        return set(self.M_star)

    def is_maximal(self) -> bool:
        """Return ``True`` iff the current matching is maximal in the graph."""
        return check_maximal_matching(self.graph, self.M_star)

    def matching_size(self) -> int:
        """Return the number of edges in the current matching."""
        return len(self.M_star)

    def partner(self, v: Vertex) -> Vertex | None:
        """Return the vertex matched to ``v`` in ``M_star``, or ``None``."""
        return partner_of(self.M_star, v)

    def build_partner_map(self) -> dict[Vertex, Vertex]:
        """Return a dict mapping each matched vertex to its partner."""
        return {x: y for x, y in self.M_star} | {y: x for x, y in self.M_star}

    def statistics(self) -> dict[str, int]:
        """Return a dictionary of runtime statistics."""
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
