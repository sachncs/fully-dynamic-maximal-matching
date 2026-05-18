"""Matching helpers and maximality checks.

These are generic graph-algorithm utilities used by the dynamic-matching
engine.  They are not specific to the paper's subgraph-system framework.
"""

from __future__ import annotations

from fdmm.graph import DynamicGraph
from fdmm.types import Matching, Vertex, canonical_edge


def greedy_maximal_matching(graph: DynamicGraph) -> Matching:
    """Return a maximal matching computed by a deterministic greedy scan.

    Vertices are processed in increasing order and the first available
    neighbour is chosen.  This guarantees determinism for a fixed graph.
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


def is_maximal_matching(graph: DynamicGraph, matching: Matching) -> bool:
    """Return ``True`` iff ``matching`` is maximal in ``graph``.

    A matching is maximal when every vertex is settled: either it is
    incident to a matching edge, or all of its neighbours are.
    """
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


def partner_of(matching: Matching, v: Vertex) -> Vertex | None:
    """Return the vertex matched to ``v`` in ``matching``, or ``None``."""
    for x, y in matching:
        if x == v:
            return y
        if y == v:
            return x
    return None


def build_partner_map(matching: Matching) -> dict[Vertex, Vertex]:
    """Return a dict mapping each matched vertex to its partner."""
    return {x: y for x, y in matching} | {y: x for x, y in matching}
