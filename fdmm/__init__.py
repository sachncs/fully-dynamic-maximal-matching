"""FDMM: A Faster Deterministic Algorithm for Fully Dynamic Maximal Matching.

Python reproduction of arXiv:2605.00797v1.
"""

from fdmm.dynamic_matching import DynamicMaximalMatching
from fdmm.graph import DynamicGraph

__all__ = ["DynamicGraph", "DynamicMaximalMatching"]
