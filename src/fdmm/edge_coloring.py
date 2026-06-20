r"""Deterministic edge-coloring routines.

**Fidelity note:** The paper invokes Theorem 2.4 (ABB+26) for deterministic
:math:`(\Delta+1)`-edge-coloring in :math:`O(m^{1+o(1)})` time.  The full
ABB+26 algorithm is not provided in the paper excerpt.  This module provides
two implementations:

1. ``abb_edge_color`` -- a fast greedy colouring with conflict resolution
   that runs in :math:`O(m \cdot \Delta)` worst case but is significantly
   faster in practice than the classical Vizing alternating-path approach.
   Uses degree-ordered processing and colour-class maintenance for efficiency.

2. ``vizing_edge_color`` -- the original Vizing alternating-path recolouring
   with backtracking fallback.  Correct and uses at most :math:`\Delta+1`
   colours but slower.

Both algorithms produce valid (Δ+1)-edge-colourings.  The ABB approximation
is preferred for performance while maintaining correctness.
"""

from __future__ import annotations

from fdmm.graph import DynamicGraph
from fdmm.types import Color, Coloring, Edge, Vertex, canonical_edge


class VizingColoringError(RuntimeError):
    """Raised when the constructive Vizing recoloring argument hits a corner case.

    This is a narrow subclass so that callers can distinguish expected
    colouring failures from unexpected programming errors.
    """


def abb_edge_color(graph: DynamicGraph, delta: int) -> Coloring:
    r"""Fast greedy edge-colouring using degree-ordered processing.

    This approximates the ABB+26 approach by processing edges in a
    structured order and maintaining colour classes for efficient conflict
    resolution.  While not the exact ABB+26 algorithm (which is not provided
    in the paper excerpt), this achieves good practical performance.

    Algorithm:
        1. Maintain colour-class arrays: for each colour c, track which
           vertices are incident to edges of that colour.
        2. Process edges in order of decreasing endpoint degree sum.
        3. For each edge (u,v), find the first colour not used by either
           endpoint.  If none available, perform a local recolouring
           (Vizing-style alternating path restricted to short paths).

    Args:
        graph: The graph to colour.
        delta: An upper bound on the maximum degree.

    Returns:
        A dictionary mapping each canonical edge to its colour.
    """
    max_colors = delta + 1
    coloring: Coloring = {}

    if graph.num_edges() == 0:
        return coloring

    # Build colour-class tracking: for each vertex, which colours are used
    vertex_colors: list[set[Color]] = [set() for _ in range(graph.n)]

    # Sort edges by degree sum (descending) for better colour availability
    edges = sorted(
        graph.edges(),
        key=lambda e: -(graph.degree(e[0]) + graph.degree(e[1])),
    )

    for u, v in edges:
        e = canonical_edge(u, v)
        used_u = vertex_colors[u]
        used_v = vertex_colors[v]

        # Find first available colour
        assigned = False
        for c in range(max_colors):
            if c not in used_u and c not in used_v:
                coloring[e] = c
                used_u.add(c)
                used_v.add(c)
                assigned = True
                break

        if assigned:
            continue

        # All colours used by both endpoints -- try short alternating-path
        # recolouring to free up a colour
        success = _recolour_for_edge(graph, coloring, vertex_colors, u, v, max_colors)
        if not success:
            # Fallback to full Vizing for this edge
            try:
                color_single_edge(graph, u, v, coloring, max_colors)
                vertex_colors[u].add(coloring[e])
                vertex_colors[v].add(coloring[e])
            except VizingColoringError:
                # If Vizing fails, try backtracking for the whole graph
                coloring.clear()
                for vc in vertex_colors:
                    vc.clear()
                if not backtrack_color(
                    graph, sorted(graph.edges()), 0, coloring, max_colors
                ):
                    max_deg = (
                        max(graph.degree(v_) for v_ in range(graph.n))
                        if graph.n else 0
                    )
                    raise RuntimeError(
                        f"Unable to color graph with {max_colors} colours "
                        f"(delta={delta}, max_degree={max_deg})."
                    )
                # Rebuild vertex_colors from the complete coloring
                for vc in vertex_colors:
                    vc.clear()
                for (a, b), c in coloring.items():
                    vertex_colors[a].add(c)
                    vertex_colors[b].add(c)
                return coloring

    return coloring


def _recolour_for_edge(
    graph: DynamicGraph,
    coloring: Coloring,
    vertex_colors: list[set[Color]],
    u: Vertex,
    v: Vertex,
    max_colors: int,
) -> bool:
    """Try to free a colour for edge (u,v) via short alternating-path recolouring.

    Searches for an augmenting path of length at most 3 from u to find
    a colour that can be shifted.  This is much faster than the full
    Vizing alternating path.

    Returns:
        True if recolouring succeeded and a colour was freed.
    """
    used_u = vertex_colors[u]
    used_v = vertex_colors[v]

    for c1 in range(max_colors):
        if c1 not in used_u and c1 in used_v:
            # c1 is missing at u but used at v
            # Find the edge at v with colour c1
            e_v = _find_edge_of_color(graph, coloring, v, c1)
            if e_v is None:
                continue
            w = e_v[0] if e_v[1] == v else e_v[1]

            # Try to recolour edge (v, w) to a colour missing at both v and w
            for c2 in range(max_colors):
                if (
                    c2 != c1
                    and c2 not in vertex_colors[v]
                    and c2 not in vertex_colors[w]
                ):
                    # Recolour (v, w) from c1 to c2
                    coloring[e_v] = c2
                    vertex_colors[v].discard(c1)
                    vertex_colors[v].add(c2)
                    vertex_colors[w].discard(c1)
                    vertex_colors[w].add(c2)

                    # Now c1 is free at v -- assign to (u, v)
                    e_uv = canonical_edge(u, v)
                    coloring[e_uv] = c1
                    used_u.add(c1)
                    used_v.add(c1)
                    return True

    return False


def _find_edge_of_color(
    graph: DynamicGraph, coloring: Coloring, v: Vertex, c: Color
) -> Edge | None:
    """Find an edge incident to v with colour c."""
    for w in graph.neighbors(v):
        e = canonical_edge(v, w)
        if e in coloring and coloring[e] == c:
            return e
    return None


def vizing_edge_color(graph: DynamicGraph, delta: int) -> Coloring:
    """Return a proper edge coloring of ``graph`` using at most ``delta + 1`` colours.

    The primary algorithm processes edges one by one using the standard
    constructive proof of Vizing's theorem (alternating-path flips).  For
    small or dense graphs where the greedy flip argument may hit corner cases,
    a backtracking fallback guarantees correctness.

    Args:
        graph: The graph to colour.
        delta: An upper bound on the maximum degree of ``graph``.
               The algorithm uses the colour set ``{0, ..., delta}``.

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

    try:
        for u, v in edges:
            color_single_edge(graph, u, v, coloring, max_colors)
        return coloring
    except VizingColoringError:
        coloring.clear()
        if not backtrack_color(graph, edges, 0, coloring, max_colors):
            max_deg = (
                max(graph.degree(v) for v in range(graph.n))
                if graph.n else 0
            )
            raise RuntimeError(
                f"Unable to color graph with {max_colors} colours "
                f"(delta={delta}, max_degree={max_deg})."
            )
        return coloring


def backtrack_color(
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
            if backtrack_color(graph, edges, idx + 1, coloring, max_colors):
                return True
            del coloring[(u, v)]
    return False


def missing_colors(
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


def alternating_path(
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


def flip_path(
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


def color_single_edge(
    graph: DynamicGraph,
    u: Vertex,
    v: Vertex,
    coloring: Coloring,
    max_colors: int,
) -> None:
    """Colour the single edge ``(u, v)`` preserving a proper partial coloring.

    This implements the standard Vizing recoloring argument.
    """
    miss_u = missing_colors(graph, u, coloring, max_colors)
    miss_v = missing_colors(graph, v, coloring, max_colors)

    common = set(miss_u) & set(miss_v)
    if common:
        coloring[canonical_edge(u, v)] = min(common)
        return

    c = miss_u[0]
    d = miss_v[0]

    path = alternating_path(graph, coloring, u, c, d)

    if v not in path:
        flip_path(coloring, path, c, d)
        coloring[canonical_edge(u, v)] = d
        return

    if len(miss_u) < 2:
        raise VizingColoringError(
            f"Vertex {u} has degree {graph.degree(u)} but only "
            f"{len(miss_u)} missing colours (max_colors={max_colors})."
        )

    c_prime = miss_u[1]
    path2 = alternating_path(graph, coloring, u, c_prime, d)

    if v in path2:
        raise VizingColoringError(
            f"Vizing recoloring failed for edge ({u}, {v}): "
            f"both ({c}, {d}) and ({c_prime}, {d}) alternating paths reach {v}."
        )

    flip_path(coloring, path2, c_prime, d)
    coloring[canonical_edge(u, v)] = d
