from __future__ import annotations

import numpy as np
from faim.core.embedding import (
    EncoderDriftReport,
    PairwiseSimilarityDiagnostics,
    encoder_drift_report,
    is_drift_acceptable,
    pairwise_similarity_report,
)
from faim.core.math import cosine_similarity

# tests/test_embedding_diagnostics.py
"""
Embedding diagnostics tests (P1.5).

Covers:
- Pairwise similarity stats.
- Encoder drift report + acceptance check.
"""


class ToyEmbedder:
    """Toy embedder with hand-crafted semantics for tests."""

    def encode(self, payload: str) -> np.ndarray:
        payload = payload.lower().strip()
        if payload in {"cat", "kitty"}:
            return np.array([1.0, 0.0], dtype=np.float32)
        if payload in {"dog", "puppy"}:
            return np.array([0.8, 0.2], dtype=np.float32)
        if payload == "car":
            return np.array([0.0, 1.0], dtype=np.float32)
        return np.zeros(2, dtype=np.float32)


class SlightlyNoisyEmbedder(ToyEmbedder):
    """Toy embedder variant with small perturbations, simulating mild drift."""

    def encode(self, payload: str) -> np.ndarray:
        v = super().encode(payload)
        if np.allclose(v, 0.0):
            return v
        noise = np.array([0.01, -0.01], dtype=np.float32)
        return (v + noise).astype(np.float32)


def test_pairwise_similarity_report_basic_stats() -> None:
    emb = ToyEmbedder()
    pairs = [("cat", "kitty"), ("cat", "dog"), ("cat", "car")]

    diag: PairwiseSimilarityDiagnostics = pairwise_similarity_report(emb, pairs)

    assert diag.count == len(pairs)
    assert -1.0 <= diag.min_similarity <= diag.max_similarity <= 1.0


def test_pairwise_similarity_report_reflects_semantics() -> None:
    emb = ToyEmbedder()

    v_cat = emb.encode("cat")
    v_kitty = emb.encode("kitty")
    v_car = emb.encode("car")

    sim_cat_kitty = cosine_similarity(v_cat, v_kitty)
    sim_cat_car = cosine_similarity(v_cat, v_car)

    # Similar animals should be closer than animal vs. car.
    assert sim_cat_kitty > sim_cat_car


def test_encoder_drift_report_high_for_similar_embedders() -> None:
    old = ToyEmbedder()
    new = SlightlyNoisyEmbedder()

    payloads = ["cat", "kitty", "dog", "car"]
    report: EncoderDriftReport = encoder_drift_report(old, new, payloads)

    assert report.count == len(payloads)
    assert 0.0 <= report.min_cosine <= report.mean_cosine <= 1.0
    assert report.mean_cosine > 0.9  # mild perturbations only


def test_is_drift_acceptable_threshold() -> None:
    old = ToyEmbedder()
    new = SlightlyNoisyEmbedder()
    payloads = ["cat", "kitty", "dog", "car"]

    report = encoder_drift_report(old, new, payloads)
    assert is_drift_acceptable(report, min_mean_cosine=0.9)
