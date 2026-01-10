# =============================================================================
# FAIM Embedder Service
# =============================================================================
# Provides text-to-vector embedding capabilities.
# Default: 'all-MiniLM-L6-v2' (dim=384) running locally.
#
# Usage:
#     embedder = get_embedder()
#     vector = embedder.embed_text("Hello world")
#     vectors = embedder.embed_batch(["Hello", "World"])
#
#     # Or using encode() for protocol compatibility:
#     vector = embedder.encode("Hello world")
# =============================================================================

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

logger = logging.getLogger(__name__)

# Type alias for vectors
Vector = List[float]


# =============================================================================
# Embedder Implementation
# =============================================================================


class Embedder:
    """
    Singleton embedder to avoid reloading model repeatedly.

    Implements both:
      - embed_text(str) / embed_batch(list) — simple API
      - encode(str) — protocol-compatible API
    """

    _instance = None
    _model = None
    _dimension: int = 384

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load the sentence-transformer model."""
        model_name = os.getenv("FAIM_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        logger.info(f"[Embedder] Loading model: {model_name}...")

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"[Embedder] Model loaded. Dim={self._dimension}, Device={self._model.device}")
        except ImportError:
            logger.error("[Embedder] sentence-transformers not installed. Using zero vectors.")
            self._model = None
        except Exception as e:
            logger.error(f"[Embedder] Failed to load model: {e}")
            self._model = None

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension

    def embed_text(self, text: str) -> Vector:
        """Embed a single string."""
        if not text or not self._model:
            return [0.0] * self._dimension

        try:
            vec = self._model.encode(text, normalize_embeddings=True)
            return vec.tolist()
        except Exception as e:
            logger.error(f"[Embedder] embed_text failed: {e}")
            return [0.0] * self._dimension

    def embed_batch(self, texts: List[str]) -> List[Vector]:
        """Embed a list of strings."""
        if not texts:
            return []
        if not self._model:
            return [[0.0] * self._dimension for _ in texts]

        try:
            vecs = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
            return vecs.tolist()
        except Exception as e:
            logger.error(f"[Embedder] embed_batch failed: {e}")
            return [[0.0] * self._dimension for _ in texts]

    def encode(self, payload: str) -> Vector:
        """Protocol-compatible alias for embed_text."""
        return self.embed_text(payload)


# =============================================================================
# Global Instance
# =============================================================================

_embedder = None


def get_embedder() -> Embedder:
    """Get the global embedder singleton."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


# =============================================================================
# Utility: Cosine Similarity
# =============================================================================


def cosine_similarity(a: Vector, b: Vector) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.asarray(a, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)

    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


# =============================================================================
# Diagnostics (Optional)
# =============================================================================


@dataclass(frozen=True)
class EmbeddingStats:
    """Statistics from embedding operations."""

    count: int
    mean_similarity: float
    min_similarity: float
    max_similarity: float


def pairwise_similarity_report(
    embedder: Embedder,
    pairs: Sequence[tuple[str, str]],
) -> EmbeddingStats:
    """Compute cosine similarity stats for payload pairs."""
    if not pairs:
        return EmbeddingStats(count=0, mean_similarity=0.0, min_similarity=0.0, max_similarity=0.0)

    sims: list[float] = []
    for a, b in pairs:
        va = embedder.encode(a)
        vb = embedder.encode(b)
        sims.append(cosine_similarity(va, vb))

    arr = np.asarray(sims, dtype=np.float64)
    return EmbeddingStats(
        count=arr.size,
        mean_similarity=float(arr.mean()),
        min_similarity=float(arr.min()),
        max_similarity=float(arr.max()),
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "Embedder",
    "Vector",
    "get_embedder",
    "cosine_similarity",
    "EmbeddingStats",
    "pairwise_similarity_report",
]
