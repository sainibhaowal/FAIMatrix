from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

import numpy as np

from .math import cosine_similarity
from .types import Vector

# faim/core/embedding.py
"""
faim.core.embedding

Embedding interfaces & diagnostics for FAIM (P1.5).

Golden Edition:
- Embedder Protocol abstraction over arbitrary encoders.
- Pairwise similarity diagnostics for semantic sanity checks.
- Encoder drift report for tracking changes across encoder versions.
"""

# ============================================================================
# Embedder protocol
# ============================================================================


@runtime_checkable
class Embedder(Protocol):
    """
    Protocol for FAIM-compatible embedders.

    Any embedder used by FAIM should implement:

        encode(payload: str) -> Vector

    This keeps FAIM logic independent of the specific encoder backend
    (LLM, sentence transformer, custom model, etc.).
    """

    def encode(self, payload: str) -> Vector:  # pragma: no cover - interface
        ...


# ============================================================================
# Pairwise similarity diagnostics
# ============================================================================


@dataclass(frozen=True)
class PairwiseSimilarityDiagnostics:
    """
    Summary statistics over embedding similarities for payload pairs.

    Attributes
    ----------
    count:
        Number of evaluated pairs.
    mean_similarity:
        Average cosine similarity across all pairs.
    min_similarity:
        Minimum cosine similarity across pairs.
    max_similarity:
        Maximum cosine similarity across pairs.
    """

    count: int
    mean_similarity: float
    min_similarity: float
    max_similarity: float


def pairwise_similarity_report(
    embedder: Embedder,
    pairs: Sequence[tuple[str, str]],
) -> PairwiseSimilarityDiagnostics:
    """
    Compute cosine similarity stats for payload pairs.

    Intended usage:
    - Construct small sets of (similar, similar) and (similar, dissimilar)
      pairs and inspect the resulting distribution.

    This is a lightweight semantic sanity check, not a full benchmark.
    """
    if not pairs:
        return PairwiseSimilarityDiagnostics(
            count=0,
            mean_similarity=0.0,
            min_similarity=0.0,
            max_similarity=0.0,
        )

    sims: list[float] = []
    for a, b in pairs:
        va = embedder.encode(a)
        vb = embedder.encode(b)
        sims.append(cosine_similarity(va, vb))

    arr = np.asarray(sims, dtype=np.float64)
    return PairwiseSimilarityDiagnostics(
        count=arr.size,
        mean_similarity=float(arr.mean()),
        min_similarity=float(arr.min()),
        max_similarity=float(arr.max()),
    )


# ============================================================================
# Encoder drift diagnostics
# ============================================================================


@dataclass(frozen=True)
class EncoderDriftReport:
    """
    Drift statistics between two embedders over a payload set.

    Attributes
    ----------
    count:
        Number of evaluated payloads.
    mean_cosine:
        Average cosine(E_old(x), E_new(x)) over all payloads.
    min_cosine:
        Minimum cosine over payloads.
    max_cosine:
        Maximum cosine over payloads.
    """

    count: int
    mean_cosine: float
    min_cosine: float
    max_cosine: float


def encoder_drift_report(
    old_embedder: Embedder,
    new_embedder: Embedder,
    payloads: Sequence[str],
) -> EncoderDriftReport:
    """
    Measure how much embeddings move when swapping encoders.

    For each payload x, this computes:

        c_x = cosine(E_old(x), E_new(x))

    Values near 1.0 indicate low drift; values near 0 or negative indicate
    large representational changes.
    """
    if not payloads:
        return EncoderDriftReport(
            count=0,
            mean_cosine=0.0,
            min_cosine=0.0,
            max_cosine=0.0,
        )

    cosines: list[float] = []
    for text in payloads:
        v_old = old_embedder.encode(text)
        v_new = new_embedder.encode(text)
        cosines.append(cosine_similarity(v_old, v_new))

    arr = np.asarray(cosines, dtype=np.float64)
    return EncoderDriftReport(
        count=arr.size,
        mean_cosine=float(arr.mean()),
        min_cosine=float(arr.min()),
        max_cosine=float(arr.max()),
    )


def is_drift_acceptable(
    report: EncoderDriftReport,
    *,
    min_mean_cosine: float = 0.95,
) -> bool:
    """
    Return True if encoder drift stays within the acceptable band.

    This does *not* log by itself – higher layers (services/CLI) can
    decide how to react (log, alert, rollback, etc.).
    """
    if report.count == 0:
        # No data → treat as trivially acceptable.
        return True
    return report.mean_cosine >= min_mean_cosine


__all__ = (
    "Embedder",
    "PairwiseSimilarityDiagnostics",
    "EncoderDriftReport",
    "pairwise_similarity_report",
    "encoder_drift_report",
    "is_drift_acceptable",
)
