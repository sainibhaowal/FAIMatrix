"""FAIM-Native Reasoning Engine: Multi-hop traversal and inference.

Provides deterministic graph traversal for complex reasoning chains.
Zero ML, fully auditable, production-grade.
"""

from __future__ import annotations

from .implications import ImplicationEngine, ImplicationRule
from .paths import PathConstraints, PathOptimizer
from .traversal import Hop, MultiHopTraverser, ReasoningPath

__all__ = [
    "MultiHopTraverser",
    "ReasoningPath",
    "Hop",
    "ImplicationEngine",
    "ImplicationRule",
    "PathOptimizer",
    "PathConstraints",
]
