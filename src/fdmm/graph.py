r"""Dynamic undirected graph with adjacency sets.

**Fidelity note:** The paper states that adjacency lists are stored as binary
search trees to support :math:`O(\log n)` insertion, deletion, and lookup.
In this Python reproduction we use the built-in ``set`` type, which provides
amortised :math:`O(1)` operations.  The asymptotic guarantees of the
algorithm are preserved; only the hidden constant factors differ.
"""

from __future__ import annotations

from collections.abc import Iterator

from fdmm.types import Edge, Vertex


class DynamicGraph:
    """A simple undirected graph that supports dynamic edge insertions and deletions.

    Attributes:
        n: Number of vertices (fixed at construction).
        adj: ``adj[v]`` is the set of neighbours of ``v``.
        edge_count: Number of edges currently in the graph.
    """

    def __init__(self, n: int) -> None:
        """Initialise an empty graph on ``n`` vertices labelled ``0 … n-1``.

        Args:
            n: Number of vertices.  Must be non-negative.

        Raises:
            ValueError: If ``n`` is negative.
        """
        if n < 0:
            raise ValueError(f"n must be non-negative, got {n}")
        self.n: int = n
        self.adj: list[set[Vertex]] = [set() for _ in range(n)]
        self.edge_count: int = 0

    def add_edge(self, u: Vertex, v: Vertex, *, strict: bool = False) -> None:
        """Insert an undirected edge ``(u, v)``.

        Duplicate insertions are silently ignored unless ``strict`` is ``True``.

        Args:
            u: One endpoint.
            v: The other endpoint.
            strict: If ``True``, raise on self-loops or duplicate edges.

        Raises:
            ValueError: If either endpoint is out of range, or if ``strict``
                is ``True`` and the edge is a self-loop or already exists.
        """
        self.validate_vertex(u)
        self.validate_vertex(v)
        if u == v:
            if strict:
                raise ValueError("Self-loops are not allowed")
            return
        added = v not in self.adj[u]
        if not added:
            if strict:
                raise ValueError(f"Edge ({u}, {v}) already exists")
            return
        self.adj[u].add(v)
        self.adj[v].add(u)
        self.edge_count += 1

    def remove_edge(self, u: Vertex, v: Vertex, *, strict: bool = False) -> None:
        """Delete an undirected edge ``(u, v)``.

        Deleting a non-existent edge is silently ignored unless ``strict`` is ``True``.

        Args:
            u: One endpoint.
            v: The other endpoint.
            strict: If ``True``, raise when the edge does not exist.

        Raises:
            ValueError: If either endpoint is out of range, or if ``strict``
                is ``True`` and the edge does not exist.
        """
        self.validate_vertex(u)
        self.validate_vertex(v)
        removed = v in self.adj[u]
        if not removed:
            if strict:
                raise ValueError(f"Edge ({u}, {v}) does not exist")
            return
        self.adj[u].discard(v)
        self.adj[v].discard(u)
        self.edge_count -= 1

    def has_edge(self, u: Vertex, v: Vertex) -> bool:
        """Return ``True`` iff the edge ``(u, v)`` exists.

        Args:
            u: One endpoint.
            v: The other endpoint.

        Raises:
            ValueError: If either endpoint is out of range.
        """
        self.validate_vertex(u)
        self.validate_vertex(v)
        return v in self.adj[u]

    def degree(self, v: Vertex) -> int:
        """Return the degree of vertex ``v``.

        Args:
            v: The vertex.

        Raises:
            ValueError: If ``v`` is out of range.
        """
        self.validate_vertex(v)
        return len(self.adj[v])

    def neighbors(self, v: Vertex) -> Iterator[Vertex]:
        """Iterate over the neighbours of ``v``.

        Args:
            v: The vertex.

        Yields:
            Neighbour vertices.

        Raises:
            ValueError: If ``v`` is out of range.
        """
        self.validate_vertex(v)
        yield from self.adj[v]

    def edges(self) -> Iterator[Edge]:
        """Iterate over all edges in the graph exactly once.

        Yields:
            Canonical edges ``(u, v)`` with ``u < v``.
        """
        for u in range(self.n):
            for v in self.adj[u]:
                if u < v:
                    yield (u, v)

    def num_edges(self) -> int:
        """Return the number of edges in the graph."""
        return self.edge_count

    def validate_vertex(self, v: Vertex) -> None:
        """Validate that ``v`` is in the range ``[0, n)``.

        Raises:
            ValueError: If ``v`` is out of range.
        """
        if not (0 <= v < self.n):
            raise ValueError(f"Vertex {v} out of range [0, {self.n})")

    def copy(self) -> DynamicGraph:
        """Return a shallow copy of the graph."""
        g = DynamicGraph(self.n)
        for u in range(self.n):
            g.adj[u] = set(self.adj[u])
        g.edge_count = self.edge_count
        return g
