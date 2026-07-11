"""Visualisation utilities for the :math:`z`-subgraph system.

This module provides ASCII and text-based visualisation of the
:math:`z`-subgraph system state, useful for debugging and educational
purposes.  The output is plain text so it can be redirected to a file,
emailed, or diffed between runs.

**Engineering utility** -- not part of the paper's baseline algorithm.

Limitations:
    * All visualisations are designed for ``n <= ~100``; larger inputs
      produce very long reports.
    * The visualisations call the heavy invariant checks (e.g.
      :meth:`ZSubgraphSystem.check_all_invariants`) and therefore have
      ``O(n + m)`` cost on top of any printing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fdmm.dynamic_matching import DynamicMaximalMatching
    from fdmm.z_system import ZSubgraphSystem


def visualise_system(system: ZSubgraphSystem, width: int = 60) -> str:
    r"""Return an ASCII representation of the :math:`z`-subgraph system.

    Shows the vertex partition ``(A, B, U)``, edges of ``M``, the
    per-vertex degree bars, the cached :math:`\Lambda(u)` and
    :math:`L(a)` lists, and the result of every invariant check.

    Args:
        system: The :math:`z`-subgraph system to visualise.
        width: Maximum line width for the output (used for the
            horizontal separators and the title banners).

    Returns:
        A multi-line string with the visualisation.

    Complexity:
        :math:`O(n + m)` because every invariant check requires a full
        pass over the graph.
    """
    lines: list[str] = []
    separator = "=" * width

    lines.append(separator)
    lines.append("Z-SUBGRAPH SYSTEM VISUALISATION")
    lines.append(separator)
    lines.append(f"  n = {system.graph.n}   z = {system.z}   |M| = {len(system.M)}")
    lines.append(
        f"  |A| = {len(system.A)}   |B| = {len(system.B)}   "
        f"|U| = {len(system.U)}   |S| = {len(system.S)}"
    )
    lines.append(separator)

    # Vertex partition
    lines.append("\nVERTEX PARTITION:")
    lines.append(f"  A = {sorted(system.A)}")
    lines.append(f"  B = {sorted(system.B)}")
    lines.append(f"  U = {sorted(system.U)}")
    lines.append(f"  S = A ∪ B = {sorted(system.S)}")

    # Degree information -- one row per vertex with a small bar chart
    # of the M-degree so that saturation in S and free capacity in U
    # are visible at a glance.
    lines.append("\nDEGREES IN M:")
    for v in range(system.graph.n):
        deg = system.degree_in_M(v)
        partition = "A" if v in system.A else ("B" if v in system.B else "U")
        bar = "█" * deg
        lines.append(f"  v{v:3d} [{partition}] deg={deg:2d} {bar}")

    # Edges in M
    lines.append(f"\nEDGES IN M ({len(system.M)} edges):")
    for e in sorted(system.M):
        u, v = e
        lines.append(f"  ({u}, {v})")

    # Cached list contents -- surfaces stale-list bugs immediately.
    if system.lambda_lists:
        lines.append("\nΛ(u) LISTS (for u ∈ U):")
        for u in sorted(system.U):
            neighbors = system.lambda_lists.get(u, [])
            lines.append(f"  Λ({u}) = {neighbors}")

    if system.L_lists:
        lines.append("\nL(a) LISTS (for a ∈ A):")
        for a in sorted(system.A):
            neighbors = system.L_lists.get(a, [])
            lines.append(f"  L({a}) = {neighbors}")

    # Invariant checks -- one line per invariant plus a combined verdict.
    lines.append("\nINVARIANT CHECKS:")
    lines.append(f"  Degree bounds:   {'✓' if system.check_degree_bounds() else '✗'}")
    lines.append(f"  U-U degree:      {'✓' if system.check_U_degree_in_U() else '✗'}")
    lines.append(f"  P1 (|N(u)∩B|≤2z): {'✓' if system.check_P1() else '✗'}")
    lines.append(f"  P2 (A→S in M):   {'✓' if system.check_P2() else '✗'}")
    lines.append(f"  Λ lists:         {'✓' if system.check_lambda_lists() else '✗'}")
    lines.append(f"  L lists:         {'✓' if system.check_L_lists() else '✗'}")
    lines.append(f"  ALL INVARIANTS:  {'✓' if system.check_all_invariants() else '✗'}")

    lines.append(separator)
    return "\n".join(lines)


def visualise_matching(algo: DynamicMaximalMatching, width: int = 60) -> str:
    """Return an ASCII representation of the current matching state.

    Lists every edge in :math:`G` with a star marker on those in
    :math:`M^*`, the matching itself, every vertex's partner, and the
    full :meth:`DynamicMaximalMatching.statistics` snapshot.

    Args:
        algo: The dynamic matching algorithm instance.
        width: Maximum line width (used for separators).

    Returns:
        A multi-line string with the visualisation.

    Complexity:
        :math:`O(n + m + |M^*|)` plus the cost of any invariant
        re-checks performed by :meth:`DynamicMaximalMatching.is_maximal`.
    """
    lines: list[str] = []
    separator = "=" * width

    lines.append(separator)
    lines.append("MATCHING STATE VISUALISATION")
    lines.append(separator)
    lines.append(f"  n = {algo.n}   mode = {algo.mode}   z = {algo.z}")
    lines.append(
        f"  |E| = {algo.graph.num_edges()}   "
        f"|M*| = {len(algo.M_star)}   "
        f"maximal = {algo.is_maximal()}"
    )
    lines.append(f"  updates since rebuild = {algo.update_count}/{algo.phase_length}")
    lines.append(separator)

    # Graph edges
    lines.append("\nGRAPH EDGES:")
    for e in sorted(algo.graph.edges()):
        u, v = e
        in_matching = e in algo.M_star
        marker = " ★" if in_matching else ""
        lines.append(f"  ({u}, {v}){marker}")

    # Matching edges
    lines.append(f"\nMATCHING M* ({len(algo.M_star)} edges):")
    for e in sorted(algo.M_star):
        u, v = e
        lines.append(f"  ({u}, {v})")

    # Vertex status
    lines.append("\nVERTEX STATUS:")
    for v in range(algo.n):
        partner = algo.partner(v)
        status = f"matched to {partner}" if partner is not None else "unmatched"
        lines.append(f"  v{v:3d}: {status}")

    # Statistics
    stats = algo.statistics()
    lines.append("\nSTATISTICS:")
    for key, value in stats.items():
        lines.append(f"  {key}: {value}")

    lines.append(separator)
    return "\n".join(lines)


def visualise_graph_adjacency(algo: DynamicMaximalMatching, width: int = 60) -> str:
    """Return an ASCII adjacency list representation of the graph.

    Args:
        algo: The dynamic matching algorithm instance.
        width: Maximum line width (used for separators).

    Returns:
        A multi-line string with the adjacency list.

    Complexity:
        :math:`O(n + m)` to enumerate every neighbour.
    """
    lines: list[str] = []
    separator = "=" * width

    lines.append(separator)
    lines.append("GRAPH ADJACENCY LIST")
    lines.append(separator)

    for v in range(algo.n):
        neighbors = sorted(algo.graph.neighbors(v))
        matched_to = algo.partner(v)
        marker = f" [matched to {matched_to}]" if matched_to is not None else ""
        lines.append(f"  v{v:3d}: {neighbors}{marker}")

    lines.append(separator)
    return "\n".join(lines)
