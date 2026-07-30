"""Encoding package __init__.py with lazy imports."""

from __future__ import annotations


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "FAIMVector":
        from encoding.vector_schema import FAIMVector

        return FAIMVector
    if name == "VECTOR_DIMENSION":
        from encoding.vector_schema import VECTOR_DIMENSION

        return VECTOR_DIMENSION
    if name == "SCHEMA_VERSION":
        from encoding.vector_schema import SCHEMA_VERSION

        return SCHEMA_VERSION
    if name == "vectorize_block":
        from encoding.text_vectorizer import vectorize_block

        return vectorize_block
    if name == "vectorize_blocks":
        from encoding.text_vectorizer import vectorize_blocks

        return vectorize_blocks
    raise AttributeError(f"module 'encoding' has no attribute '{name}'")


__all__ = [
    "FAIMVector",
    "VECTOR_DIMENSION",
    "SCHEMA_VERSION",
    "vectorize_block",
    "vectorize_blocks",
]
