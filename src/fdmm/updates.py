"""Insertion and deletion handlers.

These functions implement the update-side repair logic described in the
paper.  They are kept as standalone functions so that the work they perform
can be traced and audited independently of the main class.
"""

from __future__ import annotations

from typing import Any

from fdmm.matching import partner_of
from fdmm.types import Vertex, canonical_edge


def handle_insertion(algo: Any, u: Vertex, v: Vertex) -> None:
    """Repair data structures after inserting ``(u, v)``.

    **Fidelity note:** The paper focuses on deletions in the basic algorithm;
    insertions are repaired via Observation 2.3.  We handle the specific
    ``A-U`` insertion case mentioned in the text, then fall back to a greedy
    rebuild of ``M*``.
    """
    e = canonical_edge(u, v)

    if algo.system is not None:
        a = u if u in algo.system.A else (v if v in algo.system.A else None)
        u_vert = v if a == u else (u if v in algo.system.A else None)
        if a is not None and u_vert is not None and u_vert in algo.system.U:
            if u_vert in algo.matched_vertices and a not in algo.matched_vertices:
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
    """Repair data structures after deleting ``(u, v)``."""
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
        algo.repair_maximal_matching()

    algo.rebuild_h()
    if algo.accountant is not None:
        algo.accountant.record_deletion()


def cleanup_stale_edges(algo: Any) -> None:
    """Remove from ``M_star`` any edges that no longer exist in the graph."""
    stale = [e for e in algo.M_star if not algo.graph.has_edge(e[0], e[1])]
    for e in stale:
        algo.M_star.discard(e)
        algo.matched_vertices.discard(e[0])
        algo.matched_vertices.discard(e[1])
    if algo.accountant is not None and stale:
        algo.accountant.record_stale_cleanup(len(stale))


def rematch_vertex(algo: Any, v: Vertex) -> None:
    """Try to rematch a free vertex ``v`` using local search by partition."""
    if v in algo.matched_vertices:
        return
    if algo.system is None:
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

    for w in algo.graph.neighbors(v):
        if w not in algo.matched_vertices:
            algo.M_star.add(canonical_edge(v, w))
            algo.matched_vertices.add(v)
            algo.matched_vertices.add(w)
            return


def rematch_u(algo: Any, u: Vertex) -> None:
    r"""Rematch a free :math:`U`-vertex.

    Scan :math:`\Lambda(u)` (size :math:`O(z)`) and the set
    :math:`\hat S` of currently unmatched :math:`S`-vertices.
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

    Check incoming edges in :math:`H` for an unmatched :math:`u \in U`,
    otherwise scan :math:`\hat S`.
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
    """Rematch a free :math:`A`-vertex.

    Scan the first :math:`2\tau+1` entries of :math:`L(a)`.  By invariant I2
    (or I3 for :math:`A_1`), some encountered :math:`u` is not matched to
    :math:`A` in :math:`M^*`.  Insert :math:`(a,u)` into :math:`M^*` and
    repair the prior partner of :math:`u` if necessary.

    **Fidelity note:** The paper bounds the scan to :math:`O(r/z)` entries.
    We use the explicit constant :math:`2\tau+1` where
    :math:`\tau = 32r/z`, giving a limit of :math:`64r/z+1`.
    """
    tau = (32 * algo.phase_length) // algo.z if algo.z > 0 else 0
    limit = 2 * tau + 1
    scanned = 0

    if algo.multi is not None and a in algo.multi.A1:
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

    for w in algo.graph.neighbors(a):
        if w not in algo.matched_vertices:
            algo.M_star.add(canonical_edge(a, w))
            algo.matched_vertices.add(a)
            algo.matched_vertices.add(w)
            return
