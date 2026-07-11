"""Insertion and deletion handlers.

These functions implement the update-side repair logic described in the
paper.  They are kept as standalone functions so that the work they
perform can be traced and audited independently of the main class --
particularly useful for the :class:`UpdateAccountant` counters.

Responsibilities:
    * :func:`handle_insertion` performs the ``A-U`` insertion shortcut
      from Observation 2.3 of the paper and falls back to a greedy
      rebuild of ``M*`` if the shortcut does not apply.
    * :func:`handle_deletion` removes a deleted edge from ``M*`` if it
      was there, cleans up any stale references, and tries to rematch
      the freed endpoints locally before falling back to a rebuild.
    * :func:`rematch_u`, :func:`rematch_b`, :func:`rematch_a` implement
      the per-partition rematching routines whose scans are bounded by
      the ``2τ + 1`` constant from the paper.

Failure modes:
    * If the invariants of the :math:`z`-system drift after a batch of
      updates, :func:`handle_deletion` (and, on misses, the outer class)
      fall back to :func:`DynamicMaximalMatching.repair_maximal_matching`
      which rebuilds ``M*`` from scratch.
"""

from __future__ import annotations

from typing import Any

from fdmm.matching import partner_of
from fdmm.types import Vertex, canonical_edge


def handle_insertion(algo: Any, u: Vertex, v: Vertex) -> None:
    r"""Repair data structures after inserting ``(u, v)``.

    Algorithm:
        1. If the system has been built, look for the specific
           ``A-U`` insertion case described by Observation 2.3 of the
           paper: an already-matched U-vertex paired against an
           unmatched A-vertex via the new edge.  In that case we can
           swap the U-vertex's partner for the A-vertex in
           :math:`O(1)`.
        2. Otherwise (or if shortcut invariants fail) call
           :meth:`DynamicMaximalMatching.repair_maximal_matching`
           which rebuilds a maximal matching containing :math:`M_1`.

    **Fidelity note:** The paper focuses on deletions in the basic
    algorithm; insertions are repaired via Observation 2.3.  We handle
    the specific ``A-U`` insertion case mentioned in the text, then
    fall back to a greedy rebuild of ``M*``.

    Args:
        algo: The owning :class:`DynamicMaximalMatching` instance.
        u: First endpoint.
        v: Second endpoint.
    """
    e = canonical_edge(u, v)

    if algo.system is not None:
        # Identify which endpoint sits in A and which in U.  Only the
        # ``A-U`` insertion shortcut is cheap; anything else drops
        # through to a rebuild.
        a = u if u in algo.system.A else (v if v in algo.system.A else None)
        u_vert = v if a == u else (u if v in algo.system.A else None)
        if a is not None and u_vert is not None and u_vert in algo.system.U:
            if u_vert in algo.matched_vertices and a not in algo.matched_vertices:
                # Locate U-vertex's current matching edge and evict it.
                to_remove = None
                for x, y in algo.M_star:
                    if x == u_vert or y == u_vert:
                        to_remove = (x, y)
                        break
                if to_remove is not None:
                    algo.M_star.discard(to_remove)
                    algo.matched_vertices.discard(u_vert)
                    algo.matched_vertices.discard(
                        to_remove[0] if to_remove[1] == u_vert else to_remove[1]
                    )
                    algo.M_star.add(e)
                    algo.matched_vertices.add(a)
                    algo.matched_vertices.add(u_vert)
                    if algo.accountant is not None:
                        algo.accountant.record_insertion()
                    return
                else:
                    # State corruption: vertex marked matched but no matching edge.
                    # Fall through to greedy rebuild and count the anomaly.
                    if algo.accountant is not None:
                        algo.accountant.record_greedy_rebuild()

    algo.repair_maximal_matching()
    if algo.accountant is not None:
        algo.accountant.record_insertion()


def handle_deletion(algo: Any, u: Vertex, v: Vertex) -> None:
    r"""Repair data structures after deleting ``(u, v)``.

    Algorithm:
        1. If ``(u, v)`` was in :math:`M^*`, drop it and free
           ``u`` and ``v``.
        2. Sweep ``M^*`` for any other edges that no longer exist in
           the graph (stale entries from earlier deletes).
        3. Try to rematch the two endpoints in place via
           :func:`rematch_vertex`.
        4. If maximality is not restored, call
           :meth:`DynamicMaximalMatching.repair_maximal_matching`.
        5. Refresh the auxiliary directed graph :math:`H`.

    Args:
        algo: The owning :class:`DynamicMaximalMatching` instance.
        u: First endpoint.
        v: Second endpoint.
    """
    e = canonical_edge(u, v)
    if e in algo.M_star:
        algo.M_star.discard(e)
        algo.matched_vertices.discard(u)
        algo.matched_vertices.discard(v)

    cleanup_stale_edges(algo)
    rematch_vertex(algo, u)
    rematch_vertex(algo, v)
    cleanup_stale_edges(algo)

    if not algo.is_maximal():
        # Local repair was insufficient -- fall back to a rebuild.
        algo.repair_maximal_matching()

    algo.rebuild_h()
    if algo.accountant is not None:
        algo.accountant.record_deletion()


def cleanup_stale_edges(algo: Any) -> None:
    """Remove from ``M_star`` any edges that no longer exist in the graph.

    Such "stale" entries can accumulate when an edge is deleted while it
    is only kept in :math:`M^*` as a placeholder; sweeping ensures that
    :math:`M^*` stays a subset of the current edge set.

    Args:
        algo: The owning matcher.

    Side effects:
        Mutates ``algo.M_star`` and ``algo.matched_vertices``; records
        the number of removed edges in the accountant.
    """
    stale = [e for e in algo.M_star if not algo.graph.has_edge(e[0], e[1])]
    for e in stale:
        algo.M_star.discard(e)
        algo.matched_vertices.discard(e[0])
        algo.matched_vertices.discard(e[1])
    if algo.accountant is not None and stale:
        algo.accountant.record_stale_cleanup(len(stale))


def rematch_vertex(algo: Any, v: Vertex) -> None:
    """Try to rematch a free vertex ``v`` using local search by partition.

    Dispatches to the partition-specific routine (:func:`rematch_u`,
    :func:`rematch_b`, :func:`rematch_a`) based on which set ``v``
    belongs to in the current :math:`z`-system.  If no system has been
    built yet, falls back to a direct scan of the neighbours of ``v``.

    Args:
        algo: The owning matcher.
        v: A vertex currently unmatched in :math:`M^*`.

    Side effects:
        May add an edge to ``M^*``; may recurse into partner-rematching.
    """
    if v in algo.matched_vertices:
        return
    if algo.system is None:
        # No partition to consult -- try the first free neighbour.
        for w in algo.graph.neighbors(v):
            if w not in algo.matched_vertices:
                algo.M_star.add(canonical_edge(v, w))
                algo.matched_vertices.add(v)
                algo.matched_vertices.add(w)
                return
        return

    if v in algo.system.U:
        rematch_u(algo, v)
        return
    if v in algo.system.B:
        rematch_b(algo, v)
        return
    if v in algo.system.A:
        rematch_a(algo, v)
        return

    # Vertex not in any partition (shouldn't normally happen) -- fall
    # back to a neighbour scan to keep behaviour total.
    for w in algo.graph.neighbors(v):
        if w not in algo.matched_vertices:
            algo.M_star.add(canonical_edge(v, w))
            algo.matched_vertices.add(v)
            algo.matched_vertices.add(w)
            return


def rematch_u(algo: Any, u: Vertex) -> None:
    r"""Rematch a free :math:`U`-vertex.

    Implementation of "ProcRematchU" from the paper.  Scans
    :math:`\Lambda(u)` (size :math:`O(z)`); if no free neighbour is
    found there, scans the unmatched :math:`S`-vertices as a fallback.

    Args:
        algo: The owning matcher.
        u: The :math:`U`-vertex being rematched.

    Complexity:
        :math:`O(z + |S|)` worst case, often :math:`O(z)` in practice.
    """
    for w in algo.system.lambda_lists.get(u, []):
        if w not in algo.matched_vertices and algo.graph.has_edge(u, w):
            algo.M_star.add(canonical_edge(u, w))
            algo.matched_vertices.add(u)
            algo.matched_vertices.add(w)
            if algo.accountant is not None:
                algo.accountant.record_rematch_u_scan()
            return

    scanned = 0
    for w in algo.system.S:
        if w not in algo.matched_vertices:
            if algo.graph.has_edge(u, w):
                algo.M_star.add(canonical_edge(u, w))
                algo.matched_vertices.add(u)
                algo.matched_vertices.add(w)
                if algo.accountant is not None:
                    algo.accountant.record_rematch_u_scan(scanned + 1)
                return
        scanned += 1
    if algo.accountant is not None:
        algo.accountant.record_rematch_u_scan(scanned)


def rematch_b(algo: Any, b: Vertex) -> None:
    r"""Rematch a free :math:`B`-vertex.

    Implementation of "ProcRematchB".  Looks for an unmatched
    :math:`u \in U` whose lambda list contains ``b`` (an incoming arc
    in :math:`H`), then falls back to scanning :math:`\hat S`.

    Args:
        algo: The owning matcher.
        b: The :math:`B`-vertex being rematched.

    Complexity:
        :math:`O(|U| + |S|)` in the worst case, where :math:`|U|`
        usually dominates because ``H``'s scan is bounded by the
        number of unmatched U-vertices.
    """
    scanned = 0
    for u in algo.system.U:
        if (
            u not in algo.matched_vertices
            and b in algo.system.lambda_lists.get(u, [])
            and algo.graph.has_edge(u, b)
        ):
            algo.M_star.add(canonical_edge(u, b))
            algo.matched_vertices.add(u)
            algo.matched_vertices.add(b)
            if algo.accountant is not None:
                algo.accountant.record_rematch_b_scan(scanned + 1)
            return
        scanned += 1
    if algo.accountant is not None:
        algo.accountant.record_rematch_b_scan(scanned)

    for w in algo.system.S:
        if w not in algo.matched_vertices:
            if algo.graph.has_edge(b, w):
                algo.M_star.add(canonical_edge(b, w))
                algo.matched_vertices.add(b)
                algo.matched_vertices.add(w)
                return


def rematch_a(algo: Any, a: Vertex) -> None:
    r"""Rematch a free :math:`A`-vertex.

    Implementation of "ProcRematchA".  Scans the first :math:`2\tau + 1`
    entries of :math:`L(a)`.  By invariant (I2) -- or (I3) for
    :math:`A_1` -- some encountered :math:`u` is not matched to
    :math:`A` in :math:`M^*`.  We insert :math:`(a, u)` into
    :math:`M^*` and recurse on the prior partner of :math:`u` if
    necessary.

    **Fidelity note:** The paper bounds the scan to :math:`O(r/z)`
    entries.  We use the explicit constant :math:`2\tau + 1` where
    :math:`\tau = 32r / z`, giving a limit of :math:`64r/z + 1`.

    Args:
        algo: The owning matcher.
        a: The :math:`A`-vertex being rematched.

    Complexity:
        :math:`O(\tau) = O(r / z)` for the bounded scan, plus any
        recursive calls for freed partners.
    """
    tau = (32 * algo.phase_length) // algo.z if algo.z > 0 else 0
    limit = 2 * tau + 1
    scanned = 0

    if algo.multi is not None and a in algo.multi.A1:
        # Multi-level mode: only U-vertices inside R_1 are eligible
        # to be rematched, per the paper's recursion.
        for u in algo.system.L_lists.get(a, []):
            if u not in algo.multi.R1:
                continue
            scanned += 1
            if scanned > limit:
                break
            if u not in algo.matched_vertices and algo.graph.has_edge(a, u):
                algo.M_star.add(canonical_edge(a, u))
                algo.matched_vertices.add(a)
                algo.matched_vertices.add(u)
                if algo.accountant is not None:
                    algo.accountant.record_rematch_a_scan(scanned)
                return
            partner = partner_of(algo.M_star, u)
            if partner is not None and partner in algo.system.A:
                continue
            if partner is not None:
                algo.M_star.discard(canonical_edge(u, partner))
                algo.matched_vertices.discard(partner)
            if algo.graph.has_edge(a, u):
                algo.M_star.add(canonical_edge(a, u))
                algo.matched_vertices.add(a)
                algo.matched_vertices.add(u)
                if partner is not None:
                    rematch_vertex(algo, partner)
                if algo.accountant is not None:
                    algo.accountant.record_rematch_a_scan(scanned)
                return
    else:
        for u in algo.system.L_lists.get(a, []):
            scanned += 1
            if scanned > limit:
                break
            if u not in algo.matched_vertices and algo.graph.has_edge(a, u):
                algo.M_star.add(canonical_edge(a, u))
                algo.matched_vertices.add(a)
                algo.matched_vertices.add(u)
                if algo.accountant is not None:
                    algo.accountant.record_rematch_a_scan(scanned)
                return
            partner = partner_of(algo.M_star, u)
            if partner is not None and partner not in algo.system.A:
                if algo.graph.has_edge(a, u):
                    algo.M_star.discard(canonical_edge(u, partner))
                    algo.matched_vertices.discard(partner)
                    algo.M_star.add(canonical_edge(a, u))
                    algo.matched_vertices.add(a)
                    algo.matched_vertices.add(u)
                    if partner is not None:
                        rematch_vertex(algo, partner)
                    if algo.accountant is not None:
                        algo.accountant.record_rematch_a_scan(scanned)
                    return

    if algo.accountant is not None:
        algo.accountant.record_rematch_a_scan(scanned)

    # Fall back to a direct neighbour scan if the bounded scan found
    # no eligible partner -- rare under the invariants but kept for
    # robustness against corrupted system state.
    for w in algo.graph.neighbors(a):
        if w not in algo.matched_vertices:
            algo.M_star.add(canonical_edge(a, w))
            algo.matched_vertices.add(a)
            algo.matched_vertices.add(w)
            return
