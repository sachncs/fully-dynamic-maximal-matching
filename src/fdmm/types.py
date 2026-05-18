"""Common types, constants, and small helpers for the FDMM reproduction.

This module provides type aliases and shared definitions used across the
implementation to keep the codebase self-contained.
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
    """
    if u < v:
        return (u, v)
    return (v, u)
