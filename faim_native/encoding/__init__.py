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
    if name == "get_embedding_registry":
        from encoding.embedding_providers import get_embedding_registry

        return get_embedding_registry
    if name == "get_active_embedding_provider":
        from encoding.embedding_providers import get_active_embedding_provider

        return get_active_embedding_provider
    if name == "encode_texts":
        from encoding.embedding_providers import encode_texts

        return encode_texts
    if name == "encode_single":
        from encoding.embedding_providers import encode_single

        return encode_single
    if name == "EmbeddingProvider":
        from encoding.embedding_providers import EmbeddingProvider

        return EmbeddingProvider
    if name == "BgeM3LocalProvider":
        from encoding.embedding_providers import BgeM3LocalProvider

        return BgeM3LocalProvider
    if name == "OpenAIEmbeddingProvider":
        from encoding.embedding_providers import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider
    if name == "CustomEmbeddingProvider":
        from encoding.embedding_providers import CustomEmbeddingProvider

        return CustomEmbeddingProvider
    if name == "EmbeddingProviderRegistry":
        from encoding.embedding_providers import EmbeddingProviderRegistry

        return EmbeddingProviderRegistry
    if name == "EmbeddingModelInfo":
        from encoding.embedding_providers import EmbeddingModelInfo

        return EmbeddingModelInfo
    if name == "EmbeddingResult":
        from encoding.embedding_providers import EmbeddingResult

        return EmbeddingResult
    raise AttributeError(f"module 'encoding' has no attribute '{name}'")


__all__ = [
    "FAIMVector",
    "VECTOR_DIMENSION",
    "SCHEMA_VERSION",
    "vectorize_block",
    "vectorize_blocks",
    "get_embedding_registry",
    "get_active_embedding_provider",
    "encode_texts",
    "encode_single",
    "EmbeddingProvider",
    "BgeM3LocalProvider",
    "OpenAIEmbeddingProvider",
    "CustomEmbeddingProvider",
    "EmbeddingProviderRegistry",
    "EmbeddingModelInfo",
    "EmbeddingResult",
]
