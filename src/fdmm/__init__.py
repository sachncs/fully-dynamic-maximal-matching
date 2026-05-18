"""FDMM: A Faster Deterministic Algorithm for Fully Dynamic Maximal Matching.

Python reproduction of arXiv:2605.00797v1.
"""

from fdmm.accounting import UpdateAccountant
from fdmm.dynamic_matching import DynamicMaximalMatching
from fdmm.graph import DynamicGraph
from fdmm.invariants import check_maximal_matching, check_z_system_invariants
from fdmm.matching import build_partner_map, greedy_maximal_matching, partner_of
from fdmm.simulation import random_update_sequence, replay_updates
from fdmm.z_system import MultiLevelSystem, ZSubgraphSystem

__version__ = "0.3.0"

__all__ = [
    "DynamicGraph",
    "DynamicMaximalMatching",
    "ZSubgraphSystem",
    "MultiLevelSystem",
    "greedy_maximal_matching",
    "partner_of",
    "build_partner_map",
    "check_maximal_matching",
    "check_z_system_invariants",
    "UpdateAccountant",
    "random_update_sequence",
    "replay_updates",
]
