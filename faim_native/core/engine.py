"""FAIM-Native Engine - Canonical Import.

This module re-exports FAIMNativeEngine for backward compatibility.
The implementation is in engine_native.py.

Usage:
    from core.engine import FAIMNativeEngine
    # or
    from core.engine_native import FAIMNativeEngine
"""

from .engine_native import FAIMNativeEngine, WriteResult

__all__ = ["FAIMNativeEngine", "WriteResult"]
