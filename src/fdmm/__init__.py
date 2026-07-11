"""FDMM: A Faster Deterministic Algorithm for Fully Dynamic Maximal Matching.

This package is a pure-Python reproduction of the deterministic fully
dynamic maximal matching algorithm of Chuzhoy, Khanna, and Song
(arXiv:2605.00797v1, STOC 2026).

Two operating modes are exposed through :class:`DynamicMaximalMatching`:

* ``"basic"`` -- :math:`\\tilde O(n^{2/3})` amortised update time via a
  single-level :math:`z`-subgraph system.
* ``"multilevel"`` -- :math:`n^{1/2+o(1)}` amortised update time via a
  recursive :math:`k`-level system with :math:`k = \\Theta(\\log n)`.

The supporting modules provide:

* :class:`DynamicGraph` -- a thin adjacency-set wrapper that stands in
  for the paper's BST-based adjacency layer.
* :class:`ZSubgraphSystem` and :class:`MultiLevelSystem` -- the
  combinatorial state used by both modes.
* The :math:`z`-system construction primitives
  :func:`build_z_system`, :func:`build_multi_level_system`,
  :func:`edge_switch_inside_B`, and :func:`promote_u_vertex`.
* The edge colouring utilities :func:`abb_edge_color`,
  :func:`vizing_edge_color`, :func:`recolour_for_edge`,
  :func:`find_edge_of_color`, :func:`color_single_edge`,
  :func:`alternating_path`, and :func:`flip_path`.
* :func:`check_maximal_matching` and :func:`check_z_system_invariants`
  -- standalone invariant validators used by the test suite.
* :class:`UpdateAccountant` and the :mod:`fdmm.simulation` /
  :mod:`fdmm.parallel` modules -- engineering utilities for empirical
  benchmarking and reproducibility.

Reference:
    Chuzhoy, J., Khanna, S., Song, J. (2026).  *A Faster Deterministic
    Algorithm for Fully Dynamic Maximal Matching*.  arXiv:2605.00797v1.
"""

from fdmm.accounting import UpdateAccountant
from fdmm.dynamic_matching import DynamicMaximalMatching
from fdmm.edge_coloring import (
    abb_edge_color,
    alternating_path,
    backtrack_color,
    color_single_edge,
    find_edge_of_color,
    flip_path,
    missing_colors,
    recolour_for_edge,
    vizing_edge_color,
)
from fdmm.graph import DynamicGraph
from fdmm.invariants import check_maximal_matching, check_z_system_invariants
from fdmm.matching import build_partner_map, greedy_maximal_matching, partner_of
from fdmm.parallel import compare_modes, run_parallel_benchmarks
from fdmm.simulation import random_update_sequence, replay_updates
from fdmm.types import Edge, Matching, Vertex, canonical_edge
from fdmm.visualise import visualise_matching, visualise_system
from fdmm.z_system import (
    MultiLevelSystem,
    ZSubgraphSystem,
    build_multi_level_system,
    build_z_system,
    edge_switch_inside_B,
    promote_u_vertex,
)

__version__ = "0.4.1"

__all__ = [
    "DynamicGraph",
    "DynamicMaximalMatching",
    "ZSubgraphSystem",
    "MultiLevelSystem",
    "Edge",
    "Matching",
    "Vertex",
    "canonical_edge",
    "greedy_maximal_matching",
    "partner_of",
    "build_partner_map",
    "check_maximal_matching",
    "check_z_system_invariants",
    "UpdateAccountant",
    "random_update_sequence",
    "replay_updates",
    "visualise_system",
    "visualise_matching",
    "run_parallel_benchmarks",
    "compare_modes",
    "abb_edge_color",
    "vizing_edge_color",
    "backtrack_color",
    "missing_colors",
    "alternating_path",
    "flip_path",
    "color_single_edge",
    "recolour_for_edge",
    "find_edge_of_color",
    "build_z_system",
    "build_multi_level_system",
    "edge_switch_inside_B",
    "promote_u_vertex",
]
