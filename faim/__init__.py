"""Top-level FAIM package.

P1: minimal init so `import faim.core.*` works from tests.
"""

from __future__ import annotations

from .core.engine import FAIMEngine

__all__ = ["FAIMEngine"]
