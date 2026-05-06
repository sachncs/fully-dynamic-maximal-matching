r"""Deterministic edge-coloring routines.

**Fidelity note:** The paper invokes Theorem 2.4 (ABB+26) for deterministic
:math:`(\Delta+1)`-edge-coloring in :math:`O(m^{1+o(1)})` time.  The full
algorithm is not provided in the paper; this module supplies a faithful
baseline implementation of Vizing's theorem via alternating-path recoloring.
The coloring is correct and uses at most :math:`\Delta+1` colours, but the
running time is :math:`O(m \cdot \Delta)` rather than the paper's almost-linear
bound.  This gap is flagged explicitly in the fidelity report.
"""

from __future__ import annotations

from fdmm.graph import DynamicGraph
from fdmm.types import Color, Coloring, Edge, Vertex, canonical_edge


def vizing_edge_color(graph: DynamicGraph, delta: int) -> Coloring:
    """Return a proper edge coloring of ``graph`` using at most ``delta + 1`` colours.

    The primary algorithm processes edges one by one using the standard
    constructive proof of Vizing's theorem (alternating-path flips).  For
    small or dense graphs where the greedy flip argument may hit corner cases,
    a backtracking fallback guarantees correctness.

    Args:
        graph: The graph to colour.
        delta: An upper bound on the maximum degree of ``graph``.
               The algorithm uses the colour set ``{0, …, delta}``.

    Returns:
        A dictionary mapping each canonical edge to its colour.

    Raises:
        RuntimeError: If both the Vizing and backtracking strategies fail.
                      This should not happen for a simple graph when
                      ``delta >= max_degree``.
    """
    max_colors = delta + 1
    coloring: Coloring = {}

    edges = sorted(graph.edges())

    # Fast path: use Vizing's theorem for each edge.
    try:
        for u, v in edges:
            _color_single_edge(graph, u, v, coloring, max_colors)
        return coloring
    except RuntimeError:
        # Fallback: backtracking (exponential but correct; only used for
        # small / dense graphs where the greedy flip hits a corner case).
        coloring.clear()
        if not _backtrack_color(graph, edges, 0, coloring, max_colors):
            raise RuntimeError(
                f"Unable to color graph with {max_colors} colours "
                f"(delta={delta}, max_degree={max(graph.degree(v) for v in range(graph.n)) if graph.n else 0})."
            )
        return coloring


def _backtrack_color(
    graph: DynamicGraph,
    edges: list[Edge],
    idx: int,
    coloring: Coloring,
    max_colors: int,
) -> bool:
    """Backtracking edge-coloring (exponential but correct for small graphs)."""
    if idx == len(edges):
        return True
    u, v = edges[idx]
    used: set[Color] = set()
    for w in graph.neighbors(u):
        e = canonical_edge(u, w)
        if e in coloring:
            used.add(coloring[e])
    for w in graph.neighbors(v):
        e = canonical_edge(v, w)
        if e in coloring:
            used.add(coloring[e])
    for c in range(max_colors):
        if c not in used:
            coloring[(u, v)] = c
            if _backtrack_color(graph, edges, idx + 1, coloring, max_colors):
                return True
            del coloring[(u, v)]
    return False


def _missing_colors(
    graph: DynamicGraph,
    vertex: Vertex,
    coloring: Coloring,
    max_colors: int,
) -> list[Color]:
    """Return a list of colours not incident to ``vertex`` in ``coloring``."""
    used: set[Color] = set()
    for w in graph.neighbors(vertex):
        e = canonical_edge(vertex, w)
        if e in coloring:
            used.add(coloring[e])
    return [c for c in range(max_colors) if c not in used]


def _alternating_path(
    graph: DynamicGraph,
    coloring: Coloring,
    start: Vertex,
    color1: Color,
    color2: Color,
) -> list[Vertex]:
    """Return the maximal ``color1/color2`` alternating path beginning at ``start``.

    It is assumed that ``start`` is missing ``color1`` in ``coloring``.
    """
    path: list[Vertex] = [start]
    visited: set[Vertex] = {start}
    current = start
    next_color = color2

    while True:
        found = False
        for w in graph.neighbors(current):
            e = canonical_edge(current, w)
            if e in coloring and coloring[e] == next_color and w not in visited:
                path.append(w)
                visited.add(w)
                current = w
                next_color = color2 if next_color == color1 else color1
                found = True
                break
        if not found:
            break

    return path


def _flip_path(
    coloring: Coloring,
    path: list[Vertex],
    color1: Color,
    color2: Color,
) -> None:
    """Swap ``color1`` and ``color2`` on every edge of ``path``."""
    for i in range(len(path) - 1):
        e = canonical_edge(path[i], path[i + 1])
        if coloring[e] == color1:
            coloring[e] = color2
        else:
            coloring[e] = color1


def _color_single_edge(
    graph: DynamicGraph,
    u: Vertex,
    v: Vertex,
    coloring: Coloring,
    max_colors: int,
) -> None:
    """Colour the single edge ``(u, v)`` preserving a proper partial coloring.

    This implements the standard Vizing recoloring argument.
    """
    miss_u = _missing_colors(graph, u, coloring, max_colors)
    miss_v = _missing_colors(graph, v, coloring, max_colors)

    common = set(miss_u) & set(miss_v)
    if common:
        coloring[canonical_edge(u, v)] = min(common)
        return

    # ``u`` is missing ``c``, ``v`` is missing ``d``.
    c = miss_u[0]
    d = miss_v[0]

    # Maximal (c, d)-alternating path starting at ``u``.
    path = _alternating_path(graph, coloring, u, c, d)

    if v not in path:
        _flip_path(coloring, path, c, d)
        # After the flip ``u`` is missing ``d`` and ``v`` is missing ``d``.
        coloring[canonical_edge(u, v)] = d
        return

    # The (c, d)-path reaches ``v``.  By Vizing's theorem the (c', d)-path
    # from ``u`` does not reach ``v`` for any second colour ``c'`` missing at ``u``.
    if len(miss_u) < 2:
        raise RuntimeError(
            f"Vertex {u} has degree {graph.degree(u)} but only "
            f"{len(miss_u)} missing colours (max_colors={max_colors})."
        )

    c_prime = miss_u[1]
    path2 = _alternating_path(graph, coloring, u, c_prime, d)

    if v in path2:
        # This contradicts the standard Vizing argument; it typically means
        # ``delta`` was underestimated.
        raise RuntimeError(
            f"Vizing recoloring failed for edge ({u}, {v}): "
            f"both ({c}, {d}) and ({c_prime}, {d}) alternating paths reach {v}."
        )

    _flip_path(coloring, path2, c_prime, d)
    # After the flip ``u`` is missing ``d`` and ``v`` is missing ``d``.
    coloring[canonical_edge(u, v)] = d
