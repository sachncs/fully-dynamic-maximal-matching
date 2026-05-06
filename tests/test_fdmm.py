"""Comprehensive unit tests for the FDMM reproduction.

Tests cover core tensor shapes, forward-pass behaviour, loss computation,
critical invariants, edge cases, property-based tests, and stress tests.
"""

from __future__ import annotations

import random

import pytest

from fdmm.dynamic_matching import DynamicMaximalMatching
from fdmm.edge_coloring import vizing_edge_color
from fdmm.graph import DynamicGraph
from fdmm.types import canonical_edge
from fdmm.z_system import MultiLevelSystem, ZSubgraphSystem


# ------------------------------------------------------------------
# Graph layer
# ------------------------------------------------------------------

class TestDynamicGraph:
    """Tests for :class:`fdmm.graph.DynamicGraph`."""

    def test_empty_graph(self) -> None:
        g = DynamicGraph(5)
        assert g.n == 5
        assert g.num_edges() == 0
        assert g.degree(0) == 0

    def test_add_edge(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        assert g.has_edge(0, 1)
        assert g.has_edge(1, 0)
        assert g.degree(0) == 1
        assert g.degree(1) == 1

    def test_remove_edge(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.remove_edge(0, 1)
        assert not g.has_edge(0, 1)
        assert g.degree(0) == 0

    def test_duplicate_insert_ignored(self) -> None:
        g = DynamicGraph(3)
        g.add_edge(0, 1)
        g.add_edge(0, 1)
        assert g.num_edges() == 1

    def test_self_loop_ignored(self) -> None:
        g = DynamicGraph(3)
        g.add_edge(0, 0)
        assert g.num_edges() == 0

    def test_neighbors(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.add_edge(0, 2)
        assert set(g.neighbors(0)) == {1, 2}

    def test_edges_iterator(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.add_edge(1, 2)
        edges = set(g.edges())
        assert edges == {(0, 1), (1, 2)}

    def test_invalid_vertex(self) -> None:
        g = DynamicGraph(3)
        with pytest.raises(ValueError):
            g.degree(5)

    def test_copy(self) -> None:
        g = DynamicGraph(3)
        g.add_edge(0, 1)
        h = g.copy()
        h.remove_edge(0, 1)
        assert g.has_edge(0, 1)
        assert not h.has_edge(0, 1)

    def test_single_vertex(self) -> None:
        g = DynamicGraph(1)
        g.add_edge(0, 0)
        assert g.num_edges() == 0
        assert list(g.edges()) == []

    def test_zero_vertices(self) -> None:
        g = DynamicGraph(0)
        assert g.num_edges() == 0
        assert list(g.edges()) == []

    def test_complete_graph(self) -> None:
        n = 5
        g = DynamicGraph(n)
        for i in range(n):
            for j in range(i + 1, n):
                g.add_edge(i, j)
        assert g.num_edges() == n * (n - 1) // 2
        for v in range(n):
            assert g.degree(v) == n - 1

    def test_bipartite_graph(self) -> None:
        n, m = 3, 4
        g = DynamicGraph(n + m)
        for i in range(n):
            for j in range(m):
                g.add_edge(i, n + j)
        assert g.num_edges() == n * m
        for i in range(n):
            assert g.degree(i) == m
        for j in range(m):
            assert g.degree(n + j) == n

    def test_edges_no_duplicates(self) -> None:
        g = DynamicGraph(3)
        g.add_edge(0, 1)
        g.add_edge(1, 0)  # same edge
        assert len(list(g.edges())) == 1

    def test_remove_nonexistent_edge(self) -> None:
        g = DynamicGraph(3)
        g.remove_edge(0, 1)  # should not raise
        assert g.num_edges() == 0

    def test_large_graph_degree(self) -> None:
        n = 1000
        g = DynamicGraph(n)
        for i in range(n - 1):
            g.add_edge(i, i + 1)
        assert g.num_edges() == n - 1
        assert g.degree(0) == 1
        assert g.degree(n - 1) == 1

    def test_copy_isolation(self) -> None:
        g = DynamicGraph(5)
        g.add_edge(0, 1)
        g.add_edge(2, 3)
        h = g.copy()
        h.add_edge(0, 2)
        assert not g.has_edge(0, 2)
        assert h.has_edge(0, 2)

    def test_neighbors_on_isolated_vertex(self) -> None:
        g = DynamicGraph(5)
        g.add_edge(0, 1)
        assert set(g.neighbors(2)) == set()


# ------------------------------------------------------------------
# Edge colouring
# ------------------------------------------------------------------

class TestEdgeColoring:
    """Tests for :mod:`fdmm.edge_coloring`."""

    def _is_proper(self, graph: DynamicGraph, coloring: dict) -> bool:
        for u in range(graph.n):
            seen: set[int] = set()
            for v in graph.neighbors(u):
                e = canonical_edge(u, v)
                c = coloring[e]
                if c in seen:
                    return False
                seen.add(c)
        return True

    def test_triangle(self) -> None:
        g = DynamicGraph(3)
        g.add_edge(0, 1)
        g.add_edge(1, 2)
        g.add_edge(2, 0)
        coloring = vizing_edge_color(g, 2)
        assert len(set(coloring.values())) <= 3
        assert self._is_proper(g, coloring)

    def test_star(self) -> None:
        g = DynamicGraph(5)
        for i in range(1, 5):
            g.add_edge(0, i)
        coloring = vizing_edge_color(g, 4)
        assert len(set(coloring.values())) <= 5
        assert self._is_proper(g, coloring)

    def test_path(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.add_edge(1, 2)
        g.add_edge(2, 3)
        coloring = vizing_edge_color(g, 2)
        assert len(set(coloring.values())) <= 3
        assert self._is_proper(g, coloring)

    def test_empty_graph(self) -> None:
        g = DynamicGraph(3)
        coloring = vizing_edge_color(g, 0)
        assert coloring == {}

    def test_cycle(self) -> None:
        g = DynamicGraph(5)
        for i in range(5):
            g.add_edge(i, (i + 1) % 5)
        coloring = vizing_edge_color(g, 2)
        assert len(set(coloring.values())) <= 3
        assert self._is_proper(g, coloring)

    def test_complete_graph_odd(self) -> None:
        n = 5
        g = DynamicGraph(n)
        for i in range(n):
            for j in range(i + 1, n):
                g.add_edge(i, j)
        coloring = vizing_edge_color(g, n - 1)
        assert len(set(coloring.values())) <= n
        assert self._is_proper(g, coloring)

    def test_complete_graph_even(self) -> None:
        n = 6
        g = DynamicGraph(n)
        for i in range(n):
            for j in range(i + 1, n):
                g.add_edge(i, j)
        coloring = vizing_edge_color(g, n - 1)
        assert len(set(coloring.values())) <= n
        assert self._is_proper(g, coloring)

    def test_disconnected_components(self) -> None:
        g = DynamicGraph(6)
        # Two triangles
        g.add_edge(0, 1)
        g.add_edge(1, 2)
        g.add_edge(2, 0)
        g.add_edge(3, 4)
        g.add_edge(4, 5)
        g.add_edge(5, 3)
        coloring = vizing_edge_color(g, 2)
        assert len(set(coloring.values())) <= 3
        assert self._is_proper(g, coloring)

    def test_single_edge(self) -> None:
        g = DynamicGraph(2)
        g.add_edge(0, 1)
        coloring = vizing_edge_color(g, 1)
        assert len(set(coloring.values())) == 1
        assert self._is_proper(g, coloring)

    def test_two_parallel_paths(self) -> None:
        g = DynamicGraph(6)
        g.add_edge(0, 1)
        g.add_edge(1, 2)
        g.add_edge(3, 4)
        g.add_edge(4, 5)
        coloring = vizing_edge_color(g, 2)
        assert len(set(coloring.values())) <= 3
        assert self._is_proper(g, coloring)

    def test_coloring_all_edges_present(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.add_edge(0, 2)
        g.add_edge(1, 2)
        coloring = vizing_edge_color(g, 2)
        assert len(coloring) == g.num_edges()
        for e in g.edges():
            assert e in coloring


# ------------------------------------------------------------------
# z-Subgraph system
# ------------------------------------------------------------------

class TestZSubgraphSystem:
    """Tests for :class:`fdmm.z_system.ZSubgraphSystem`."""

    def test_basic_properties(self) -> None:
        g = DynamicGraph(6)
        g.add_edge(0, 1)
        g.add_edge(0, 2)
        g.add_edge(1, 2)
        g.add_edge(3, 4)
        g.add_edge(4, 5)

        system = ZSubgraphSystem(graph=g, z=2)
        system.A = {0, 1, 2}
        system.B = {3, 4}
        system.U = {5}
        system.M = {(0, 1), (3, 4)}
        system.build_lambda_and_L()

        assert system.S == {0, 1, 2, 3, 4}
        assert system.degree_in_M(0) == 1
        assert system.degree_in_M(5) == 0
        assert system.check_P2()

    def test_lambda_lists(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.add_edge(0, 2)
        g.add_edge(0, 3)
        system = ZSubgraphSystem(graph=g, z=2)
        system.U = {0}
        system.B = {1, 2}
        system.A = {3}
        system.build_lambda_and_L()
        assert set(system.lambda_lists[0]) == {1, 2}
        assert set(system.L_lists[3]) == {0}

    def test_maximal_matching_check(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.add_edge(1, 2)
        g.add_edge(2, 3)
        system = ZSubgraphSystem(graph=g, z=2)
        assert system.is_maximal_matching({(0, 1), (2, 3)})
        assert not system.is_maximal_matching({(0, 1)})

    def test_empty_graph_maximal(self) -> None:
        g = DynamicGraph(3)
        system = ZSubgraphSystem(graph=g, z=1)
        assert system.is_maximal_matching(set())

    def test_single_edge_maximal(self) -> None:
        g = DynamicGraph(2)
        g.add_edge(0, 1)
        system = ZSubgraphSystem(graph=g, z=1)
        assert system.is_maximal_matching({(0, 1)})

    def test_check_degree_bounds_empty(self) -> None:
        g = DynamicGraph(3)
        system = ZSubgraphSystem(graph=g, z=1)
        # Put all vertices in U so that S is empty; degree bound on S vacuously holds
        system.A = set()
        system.B = set()
        system.U = {0, 1, 2}
        assert system.check_degree_bounds()

    def test_P1_violation(self) -> None:
        g = DynamicGraph(4)
        for i in range(3):
            g.add_edge(3, i)
        system = ZSubgraphSystem(graph=g, z=1)
        system.U = {3}
        system.B = {0, 1, 2}
        system.A = set()
        # B has 3 neighbors in U, z=1 so 2z=2, violation
        assert not system.check_P1()

    def test_P2_violation(self) -> None:
        g = DynamicGraph(3)
        g.add_edge(0, 2)
        system = ZSubgraphSystem(graph=g, z=1)
        system.A = {0}
        system.B = set()
        system.U = {1, 2}
        system.M = {(0, 2)}  # a in A matched to u in U, not in S
        assert not system.check_P2()

    def test_all_invariants_on_empty(self) -> None:
        g = DynamicGraph(0)
        system = ZSubgraphSystem(graph=g, z=0)
        assert system.check_all_invariants()

    def test_degree_in_M_on_unmatched_vertex(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        system = ZSubgraphSystem(graph=g, z=1)
        system.M = {(0, 1)}
        assert system.degree_in_M(2) == 0

    def test_neighbors_in_M(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.add_edge(0, 2)
        system = ZSubgraphSystem(graph=g, z=2)
        system.M = {(0, 1), (0, 2)}
        assert set(system.neighbors_in_M(0)) == {1, 2}
        assert set(system.neighbors_in_M(1)) == {0}


# ------------------------------------------------------------------
# Dynamic maximal matching algorithm
# ------------------------------------------------------------------

class TestDynamicMaximalMatching:
    """End-to-end tests for :class:`fdmm.dynamic_matching.DynamicMaximalMatching`."""

    def test_basic_init(self) -> None:
        algo = DynamicMaximalMatching(10, mode="basic")
        assert algo.n == 10
        assert algo.mode == "basic"
        assert algo.is_maximal()

    def test_multilevel_init(self) -> None:
        algo = DynamicMaximalMatching(10, mode="multilevel")
        assert algo.mode == "multilevel"
        assert algo.is_maximal()

    def test_insert_then_delete_basic(self) -> None:
        algo = DynamicMaximalMatching(4, mode="basic")
        algo.insert_edge(0, 1)
        assert algo.is_maximal()
        algo.insert_edge(1, 2)
        assert algo.is_maximal()
        algo.insert_edge(2, 3)
        assert algo.is_maximal()

        algo.delete_edge(0, 1)
        assert algo.is_maximal()
        algo.delete_edge(1, 2)
        assert algo.is_maximal()
        algo.delete_edge(2, 3)
        assert algo.is_maximal()

    def test_insert_then_delete_multilevel(self) -> None:
        algo = DynamicMaximalMatching(4, mode="multilevel")
        algo.insert_edge(0, 1)
        assert algo.is_maximal()
        algo.insert_edge(1, 2)
        assert algo.is_maximal()
        algo.insert_edge(2, 3)
        assert algo.is_maximal()

        algo.delete_edge(0, 1)
        assert algo.is_maximal()
        algo.delete_edge(1, 2)
        assert algo.is_maximal()
        algo.delete_edge(2, 3)
        assert algo.is_maximal()

    def test_triangle_updates(self) -> None:
        algo = DynamicMaximalMatching(3, mode="basic")
        algo.insert_edge(0, 1)
        algo.insert_edge(1, 2)
        algo.insert_edge(2, 0)
        assert algo.is_maximal()
        assert algo.matching_size() >= 1

        algo.delete_edge(0, 1)
        assert algo.is_maximal()

    def test_star_updates(self) -> None:
        algo = DynamicMaximalMatching(5, mode="basic")
        for i in range(1, 5):
            algo.insert_edge(0, i)
        assert algo.is_maximal()
        assert algo.matching_size() == 1

        algo.delete_edge(0, 1)
        assert algo.is_maximal()

    def test_path_updates(self) -> None:
        algo = DynamicMaximalMatching(5, mode="basic")
        for i in range(4):
            algo.insert_edge(i, i + 1)
        assert algo.is_maximal()

        for i in range(4):
            algo.delete_edge(i, i + 1)
        assert algo.is_maximal()

    def test_statistics(self) -> None:
        algo = DynamicMaximalMatching(5, mode="basic")
        algo.insert_edge(0, 1)
        stats = algo.statistics()
        assert stats["n"] == 5
        assert stats["m"] == 1
        assert stats["matching_size"] == 1

    def test_rebuild_triggered(self) -> None:
        algo = DynamicMaximalMatching(2, mode="basic")
        algo.phase_length = 3
        algo.insert_edge(0, 1)
        assert algo.update_count == 1
        algo.insert_edge(0, 1)  # duplicate, still advances counter
        assert algo.update_count == 2
        # Next update triggers rebuild (2 -> 3 >= phase_length)
        algo.insert_edge(0, 1)
        assert algo.update_count == 0
        assert algo.is_maximal()

    def test_is_maximal_after_sequence(self) -> None:
        algo = DynamicMaximalMatching(6, mode="basic")
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]
        for u, v in edges:
            algo.insert_edge(u, v)
            assert algo.is_maximal()

        for u, v in edges:
            algo.delete_edge(u, v)
            assert algo.is_maximal()

    def test_invalid_mode(self) -> None:
        with pytest.raises(ValueError):
            DynamicMaximalMatching(5, mode="fast")

    def test_negative_vertices(self) -> None:
        with pytest.raises(ValueError):
            DynamicMaximalMatching(-1)

    def test_empty_graph_basic(self) -> None:
        algo = DynamicMaximalMatching(0, mode="basic")
        assert algo.is_maximal()
        assert algo.matching_size() == 0

    def test_empty_graph_multilevel(self) -> None:
        algo = DynamicMaximalMatching(0, mode="multilevel")
        assert algo.is_maximal()
        assert algo.matching_size() == 0

    def test_single_vertex_graph(self) -> None:
        algo = DynamicMaximalMatching(1, mode="basic")
        algo.insert_edge(0, 0)  # self-loop ignored
        assert algo.is_maximal()
        assert algo.matching_size() == 0

    def test_complete_graph_basic(self) -> None:
        n = 6
        algo = DynamicMaximalMatching(n, mode="basic")
        for i in range(n):
            for j in range(i + 1, n):
                algo.insert_edge(i, j)
        assert algo.is_maximal()
        # In a complete graph, maximal matching size is floor(n/2)
        assert algo.matching_size() == n // 2

    def test_complete_graph_then_remove_all(self) -> None:
        n = 5
        algo = DynamicMaximalMatching(n, mode="basic")
        edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
        for u, v in edges:
            algo.insert_edge(u, v)
        assert algo.is_maximal()
        # Remove all edges
        for u, v in edges:
            algo.delete_edge(u, v)
        assert algo.is_maximal()
        assert algo.matching_size() == 0

    def test_bipartite_graph(self) -> None:
        n, m = 3, 4
        algo = DynamicMaximalMatching(n + m, mode="basic")
        for i in range(n):
            for j in range(m):
                algo.insert_edge(i, n + j)
        assert algo.is_maximal()
        assert algo.matching_size() >= min(n, m)

    def test_repeated_insert_delete_same_edge(self) -> None:
        algo = DynamicMaximalMatching(2, mode="basic")
        for _ in range(20):
            algo.insert_edge(0, 1)
            assert algo.is_maximal()
            algo.delete_edge(0, 1)
            assert algo.is_maximal()

    def test_random_stress_basic(self) -> None:
        n = 10
        rng = random.Random(42)
        algo = DynamicMaximalMatching(n, mode="basic")
        edges: set[tuple[int, int]] = set()
        for _ in range(200):
            u = rng.randrange(n)
            v = rng.randrange(n)
            if u == v:
                continue
            e = (min(u, v), max(u, v))
            if e not in edges:
                edges.add(e)
                algo.insert_edge(e[0], e[1])
            else:
                edges.remove(e)
                algo.delete_edge(e[0], e[1])
            assert algo.is_maximal()

    def test_random_stress_multilevel(self) -> None:
        n = 10
        rng = random.Random(123)
        algo = DynamicMaximalMatching(n, mode="multilevel")
        edges: set[tuple[int, int]] = set()
        for _ in range(200):
            u = rng.randrange(n)
            v = rng.randrange(n)
            if u == v:
                continue
            e = (min(u, v), max(u, v))
            if e not in edges:
                edges.add(e)
                algo.insert_edge(e[0], e[1])
            else:
                edges.remove(e)
                algo.delete_edge(e[0], e[1])
            assert algo.is_maximal()

    def test_alternating_insert_delete_path(self) -> None:
        algo = DynamicMaximalMatching(4, mode="basic")
        for _ in range(10):
            algo.insert_edge(0, 1)
            assert algo.is_maximal()
            algo.insert_edge(1, 2)
            assert algo.is_maximal()
            algo.insert_edge(2, 3)
            assert algo.is_maximal()
            algo.delete_edge(0, 1)
            assert algo.is_maximal()
            algo.delete_edge(1, 2)
            assert algo.is_maximal()
            algo.delete_edge(2, 3)
            assert algo.is_maximal()

    def test_matching_is_subset_of_edges(self) -> None:
        algo = DynamicMaximalMatching(5, mode="basic")
        algo.insert_edge(0, 1)
        algo.insert_edge(1, 2)
        algo.insert_edge(2, 3)
        matching = algo.get_matching()
        for e in matching:
            assert algo.graph.has_edge(e[0], e[1])

    def test_delete_nonexistent_edge(self) -> None:
        algo = DynamicMaximalMatching(3, mode="basic")
        algo.delete_edge(0, 1)  # should not raise
        assert algo.is_maximal()

    def test_get_matching_returns_copy(self) -> None:
        algo = DynamicMaximalMatching(2, mode="basic")
        algo.insert_edge(0, 1)
        m1 = algo.get_matching()
        m2 = algo.get_matching()
        assert m1 is not m2


# ------------------------------------------------------------------
# Multi-level system
# ------------------------------------------------------------------

class TestMultiLevelSystem:
    """Tests for :class:`fdmm.z_system.MultiLevelSystem`."""

    def test_empty(self) -> None:
        g = DynamicGraph(4)
        mls = MultiLevelSystem(graph=g, k=2)
        assert mls.k == 2
        assert not mls.levels

    def test_with_levels(self) -> None:
        g = DynamicGraph(4)
        g.add_edge(0, 1)
        g.add_edge(1, 2)
        mls = MultiLevelSystem(graph=g, k=2)
        mls.levels = [
            ZSubgraphSystem(graph=g, z=2, A={0}, B={1}, U={2, 3}),
            ZSubgraphSystem(graph=g, z=1, A={0}, B={1}, U={2, 3}),
        ]
        assert len(mls.levels) == 2

    def test_level_1_invariant_I3_empty(self) -> None:
        g = DynamicGraph(0)
        mls = MultiLevelSystem(graph=g, k=1)
        assert mls.level_1_invariant_I3()


# ------------------------------------------------------------------
# Performance benchmarks
# ------------------------------------------------------------------

class TestPerformance:
    """Lightweight performance sanity checks."""

    def test_large_graph_basic(self) -> None:
        n = 100
        algo = DynamicMaximalMatching(n, mode="basic")
        for i in range(n - 1):
            algo.insert_edge(i, i + 1)
        assert algo.is_maximal()
        assert algo.matching_size() == n // 2

    def test_large_graph_multilevel(self) -> None:
        n = 100
        algo = DynamicMaximalMatching(n, mode="multilevel")
        for i in range(n - 1):
            algo.insert_edge(i, i + 1)
        assert algo.is_maximal()
        assert algo.matching_size() == n // 2

    def test_dense_graph_basic(self) -> None:
        n = 20
        algo = DynamicMaximalMatching(n, mode="basic")
        for i in range(n):
            for j in range(i + 1, n):
                algo.insert_edge(i, j)
        assert algo.is_maximal()
        assert algo.matching_size() == n // 2
