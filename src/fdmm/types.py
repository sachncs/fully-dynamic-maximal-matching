"""Shared type aliases and small helpers used throughout the FDMM package.

This module collects the minimal vocabulary used by every other module so
that downstream code can refer to a single canonical type definition
instead of restating ``tuple[int, int]`` or ``set[tuple[int, int]]`` in
many places.

Design notes:
    * Vertices are plain ``int`` labels rather than a wrapper class.  This
      keeps arithmetic cheap and lets the package interoperate naturally
      with NumPy arrays and other integer-keyed data structures used in
      benchmarks.
    * Edges are unordered and always stored in canonical form
      ``(min, max)`` so equality comparisons and set membership behave
      symmetrically regardless of call-site order.
    * Matchings are ``set[Edge]`` because the paper's algorithms rely on
      O(1) addition, removal, and membership tests when repairing a
      matching under dynamic updates.

Assumptions:
    * Vertex labels are dense and consecutive starting at ``0``; see
      :class:`fdmm.graph.DynamicGraph` for the corresponding invariant.

Limitations:
    * No support for parallel edges or self-loops.  Callers must filter
      these out (or rely on :meth:`DynamicGraph.add_edge`) before
      constructing an :data:`Edge`.
"""

from __future__ import annotations

from typing import TypeAlias

Vertex: TypeAlias = int
"""A vertex is represented by a non-negative integer."""

Edge: TypeAlias = tuple[Vertex, Vertex]
"""An undirected edge is an unordered pair of vertices.

For canonical ordering we enforce ``u < v`` internally where possible.
"""

Matching: TypeAlias = set[Edge]
"""A matching is a set of edges without common vertices."""

Color: TypeAlias = int
"""An edge color is represented by a non-negative integer."""

Coloring: TypeAlias = dict[Edge, Color]
"""A proper edge coloring maps each edge to a color."""


def canonical_edge(u: Vertex, v: Vertex) -> Edge:
    """Return the canonical (unordered) representation of an edge.

    Args:
        u: One endpoint.
        v: The other endpoint.

    Returns:
        A tuple ``(min, max)`` so that ``u < v``.

    Examples:
        >>> canonical_edge(3, 1)
        (1, 3)
        >>> canonical_edge(2, 5) == canonical_edge(5, 2)
        True
    """
    if u < v:
        return (u, v)
    return (v, u)
