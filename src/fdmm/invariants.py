"""Invariant checkers for the :math:`z`-subgraph system and maximal matching.

These functions provide standalone validation that can be called from tests
or debugging scripts.  They do not modify state.
"""

from __future__ import annotations

from fdmm.graph import DynamicGraph
from fdmm.types import Matching, Vertex
from fdmm.z_system import MultiLevelSystem, ZSubgraphSystem


def check_z_system_invariants(system: ZSubgraphSystem) -> bool:
    """Return ``True`` iff every invariant of ``system`` holds."""
    return system.check_all_invariants()


def check_maximal_matching(graph: DynamicGraph, matching: Matching) -> bool:
    """Return ``True`` iff ``matching`` is maximal in ``graph``."""
    matched_vertices: set[Vertex] = set()
    for u, v in matching:
        matched_vertices.add(u)
        matched_vertices.add(v)

    for u in range(graph.n):
        if u in matched_vertices:
            continue
        for w in graph.neighbors(u):
            if w not in matched_vertices:
                return False
    return True


def check_multi_level_i3(multi: MultiLevelSystem) -> bool:
    """Return ``True`` iff invariant I3 is satisfied.

    **Fidelity note:** The paper states I3 as ``O(r / z)`` but does not give
    the exact constant in the excerpt.  The level-1 method therefore raises
    :class:`NotImplementedError`.  This checker catches that exception and
    returns ``False`` so that the invariant is never silently accepted.
    """
    try:
        return multi.level_1_invariant_I3()
    except NotImplementedError:
        return False
