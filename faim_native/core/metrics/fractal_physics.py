"""FAIM-Native Fractal Physics.

Deterministic diagnostics for D (dimension), H (entropy), λ (evolution pressure).

Constants:
- PHI = (1 + sqrt(5)) / 2 (golden ratio)
- s = 1/PHI (scaling factor)

NO ML MODELS. NO RANDOMNESS. NO NUMPY.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# Constants
# =============================================================================

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0  # Golden ratio ≈ 1.618
GOLDEN_S: float = 1.0 / PHI  # Scaling factor ≈ 0.618

# Precision for deterministic rounding
PRECISION_DECIMALS: int = 10


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class FractalConfig:
    """Configuration for fractal diagnostics.

    Attributes:
        s_default: Default scaling factor (1/PHI).
        epsilons: List of epsilon values for D estimation.
        bins: Number of bins for entropy histogram.
        clamp_eps: Small epsilon for clamping.
        precision_decimals: Decimal precision for rounding.
        d_max: Maximum D value (based on vector dimension).
        lambda_weights: Weights for λ computation (novelty, redundancy, entropy).
    """

    s_default: float = GOLDEN_S
    epsilons: Tuple[float, ...] = (0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0)
    bins: int = 20
    clamp_eps: float = 1e-10
    precision_decimals: int = PRECISION_DECIMALS
    d_max: float = 10.0
    lambda_weights: Tuple[float, float, float] = (0.50, 0.30, 0.20)


# Default config
DEFAULT_CONFIG = FractalConfig()


# =============================================================================
# Diagnostics Result
# =============================================================================


@dataclass(frozen=True)
class FractalDiagnostics:
    """Result of fractal diagnostics computation.

    Attributes:
        graph_id: Graph identifier.
        region_id: Region identifier (or "global").
        node_count: Number of nodes analyzed.
        edge_count: Number of edges.
        s: Scaling factor used.
        D_hat: Estimated fractal dimension.
        H_hat: Estimated entropy/disorder.
        lambda_hat: Evolution pressure estimate.
        redundancy_R: Redundancy measure.
        novelty_N: Novelty measure.
        energy_E: Energy/boundedness measure.
        computed_at_version: Graph version when computed.
        diagnostics_hash: SHA256 of canonical JSON.
    """

    graph_id: str
    region_id: str
    node_count: int
    edge_count: int
    s: float
    D_hat: float
    H_hat: float
    lambda_hat: float
    redundancy_R: float
    novelty_N: float
    energy_E: float
    computed_at_version: int
    diagnostics_hash: str

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Return canonical dict for hashing (stable ordering)."""
        return {
            "D_hat": round(self.D_hat, PRECISION_DECIMALS),
            "H_hat": round(self.H_hat, PRECISION_DECIMALS),
            "edge_count": self.edge_count,
            "energy_E": round(self.energy_E, PRECISION_DECIMALS),
            "graph_id": self.graph_id,
            "lambda_hat": round(self.lambda_hat, PRECISION_DECIMALS),
            "node_count": self.node_count,
            "novelty_N": round(self.novelty_N, PRECISION_DECIMALS),
            "redundancy_R": round(self.redundancy_R, PRECISION_DECIMALS),
            "region_id": self.region_id,
            "s": round(self.s, PRECISION_DECIMALS),
            "version": self.computed_at_version,
        }

    def to_event_payload(self) -> Dict[str, Any]:
        """Return payload for DIAGNOSTICS_SNAPSHOT event."""
        return {
            "graph_id": self.graph_id,
            "region_id": self.region_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "s": round(self.s, 6),
            "D_hat": round(self.D_hat, 6),
            "H_hat": round(self.H_hat, 6),
            "lambda_hat": round(self.lambda_hat, 6),
            "redundancy_R": round(self.redundancy_R, 6),
            "novelty_N": round(self.novelty_N, 6),
            "energy_E": round(self.energy_E, 6),
            "graph_version": self.computed_at_version,
            "diagnostics_hash": self.diagnostics_hash,
        }

    def to_metrics_snapshot(
        self,
        graph_hash: str,
    ):
        """Convert to MetricsSnapshot for UI/API contract.

        Args:
            graph_hash: Hash of graph state.

        Returns:
            MetricsSnapshot with metrics dict using METRIC_KEYS_ORDERED.
        """
        # Import here to avoid circular import
        from .metrics_defs import MetricKey, MetricsSnapshot

        # Build metrics dict using contract keys
        metrics = {
            MetricKey.CR: (
                round(self.node_count / max(1, self.edge_count), 6)
                if self.edge_count
                else 0.0
            ),
            MetricKey.D_HAT: round(self.D_hat, 6),
            MetricKey.ENERGY: round(self.energy_E, 6),
            MetricKey.H_HAT: round(self.H_hat, 6),
            MetricKey.LAMBDA_HAT: round(self.lambda_hat, 6),
            MetricKey.NOVELTY: round(self.novelty_N, 6),
            MetricKey.R: round(self.redundancy_R, 6),
        }

        return MetricsSnapshot(
            graph_id=self.graph_id,
            graph_version=self.computed_at_version,
            graph_hash=graph_hash,
            metrics=metrics,
            diagnostics_hash=self.diagnostics_hash,
            created_at=None,
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _clamp01(value: float) -> float:
    """Clamp value to [0, 1]."""
    return max(0.0, min(1.0, value))


def _quantize(value: float, decimals: int = PRECISION_DECIMALS) -> float:
    """Quantize value to fixed precision."""
    return round(value, decimals)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def _cosine_distance(a: List[float], b: List[float]) -> float:
    """Compute cosine distance (1 - similarity) in [0, 2]."""
    return 1.0 - _cosine_similarity(a, b)


# =============================================================================
# Core Estimators
# =============================================================================


def compute_scaling_s(config: FractalConfig = DEFAULT_CONFIG) -> float:
    """Compute scaling factor s.

    Default: s = 1/PHI (golden ratio reciprocal).

    Args:
        config: Fractal configuration.

    Returns:
        Quantized scaling factor in (0, 1].
    """
    s = config.s_default
    return _quantize(s, config.precision_decimals)


def estimate_D_fractal(
    vectors: List[List[float]],
    epsilons: Tuple[float, ...] = DEFAULT_CONFIG.epsilons,
    config: FractalConfig = DEFAULT_CONFIG,
    distances: Optional[List[float]] = None,
) -> float:
    """Estimate fractal dimension D using correlation-dimension style.

    Algorithm:
    1. Compute pairwise cosine distances
    2. For each epsilon: count pairs with distance <= epsilon
    3. Compute slope of log(C(eps)) vs log(eps)
    4. Clamp to [0, d_max]

    Args:
        vectors: List of v_native vectors.
        epsilons: List of epsilon thresholds.
        config: Fractal configuration.
        distances: Optional precomputed pairwise (1 - similarity) values in
            stable i < j order, letting callers vectorize the quadratic
            distance pass while keeping this module numpy-free.

    Returns:
        Estimated fractal dimension D_hat in [0, d_max].
    """
    n = len(vectors)

    if n < 2:
        return 0.0

    # Compute pairwise distances (stable iteration order: i < j)
    if distances is None:
        distances = []
        for i in range(n):
            for j in range(i + 1, n):
                dist = _cosine_distance(vectors[i], vectors[j])
                distances.append(dist)

    if not distances:
        return 0.0

    # Sort epsilons for consistency
    epsilons_sorted = sorted(epsilons)

    # Compute C(eps) for each epsilon
    # C(eps) = (# pairs with dist <= eps) / (total pairs)
    total_pairs = len(distances)
    log_eps_list = []
    log_C_list = []

    for eps in epsilons_sorted:
        if eps <= 0:
            continue
        count = sum(1 for d in distances if d <= eps)
        if count > 0:
            C_eps = count / total_pairs
            log_eps_list.append(math.log(eps))
            log_C_list.append(math.log(C_eps))

    if len(log_eps_list) < 2:
        return 0.0

    # Linear regression: D = slope of log(C) vs log(eps)
    # Using least squares: D = Σ(xy) / Σ(x²) where x = log(eps), y = log(C)
    n_points = len(log_eps_list)
    mean_x = sum(log_eps_list) / n_points
    mean_y = sum(log_C_list) / n_points

    numerator = sum(
        (x - mean_x) * (y - mean_y)
        for x, y in zip(log_eps_list, log_C_list, strict=False)
    )
    denominator = sum((x - mean_x) ** 2 for x in log_eps_list)

    if abs(denominator) < config.clamp_eps:
        return 0.0

    D_hat = numerator / denominator

    # Clamp to [0, d_max]
    D_hat = max(0.0, min(config.d_max, D_hat))

    return _quantize(D_hat, config.precision_decimals)


def estimate_H_entropy(
    similarities: List[float],
    bins: int = DEFAULT_CONFIG.bins,
    config: FractalConfig = DEFAULT_CONFIG,
) -> float:
    """Estimate entropy/disorder H from similarity distribution.

    Algorithm:
    1. Build histogram of similarities across [-1, 1]
    2. Compute normalized Shannon entropy in [0, 1]

    Higher H = more disorder/diversity.
    Lower H = more concentration/uniformity.

    Args:
        similarities: List of pairwise similarity values.
        bins: Number of histogram bins.
        config: Fractal configuration.

    Returns:
        Entropy H_hat in [0, 1].
    """
    if not similarities or bins < 1:
        return 0.0

    # Build histogram over [-1, 1]
    bin_width = 2.0 / bins
    histogram = [0] * bins

    for sim in similarities:
        # Clamp to [-1, 1]
        sim = max(-1.0, min(1.0, sim))
        # Map to bin index
        idx = int((sim + 1.0) / bin_width)
        idx = min(idx, bins - 1)
        histogram[idx] += 1

    total = sum(histogram)
    if total == 0:
        return 0.0

    # Compute Shannon entropy
    H = 0.0
    for count in histogram:
        if count > 0:
            p = count / total
            H -= p * math.log(p)

    # Normalize to [0, 1] by dividing by max entropy (log(bins))
    max_H = math.log(bins)
    if max_H > 0:
        H_hat = H / max_H
    else:
        H_hat = 0.0

    return _quantize(_clamp01(H_hat), config.precision_decimals)


def compute_redundancy_R(
    similarities: List[float],
    threshold: float = 0.9,
    config: FractalConfig = DEFAULT_CONFIG,
) -> float:
    """Compute redundancy R from similarity distribution.

    R = fraction of pairs with similarity > threshold.

    Higher R = more redundancy (many similar pairs).

    Args:
        similarities: List of pairwise similarities.
        threshold: Threshold for "high similarity".
        config: Fractal configuration.

    Returns:
        Redundancy R in [0, 1].
    """
    if not similarities:
        return 0.0

    high_sim_count = sum(1 for s in similarities if s > threshold)
    R = high_sim_count / len(similarities)

    return _quantize(_clamp01(R), config.precision_decimals)


def compute_novelty_N(
    residuals: List[float],
    config: FractalConfig = DEFAULT_CONFIG,
) -> float:
    """Compute novelty N from residual distribution.

    N = mean of residuals (where residual = 1 - inheritance_fit).

    Higher N = more novel content.

    Args:
        residuals: List of node residuals.
        config: Fractal configuration.

    Returns:
        Novelty N in [0, 1].
    """
    if not residuals:
        return 0.0

    N = sum(residuals) / len(residuals)

    return _quantize(_clamp01(N), config.precision_decimals)


def estimate_lambda(
    novelty_N: float,
    redundancy_R: float,
    H_hat: float,
    config: FractalConfig = DEFAULT_CONFIG,
) -> float:
    """Estimate evolution pressure λ.

    λ = w0 * N + w1 * (1 - R) + w2 * H

    where:
    - N = novelty (more novel = higher λ)
    - 1-R = non-redundancy (less redundancy = higher λ)
    - H = entropy (more diverse = higher λ)

    Higher λ = more pressure to evolve/discover.

    Args:
        novelty_N: Novelty measure in [0, 1].
        redundancy_R: Redundancy measure in [0, 1].
        H_hat: Entropy in [0, 1].
        config: Fractal configuration.

    Returns:
        Evolution pressure λ_hat in [0, 1].
    """
    w_n, w_r, w_h = config.lambda_weights

    lambda_hat = w_n * novelty_N + w_r * (1.0 - redundancy_R) + w_h * H_hat

    return _quantize(_clamp01(lambda_hat), config.precision_decimals)


def compute_energy_E(
    vectors: List[List[float]],
    s: float = GOLDEN_S,
    config: FractalConfig = DEFAULT_CONFIG,
) -> float:
    """Compute energy/boundedness measure E.

    E = mean L2 norm of vectors, scaled by s.

    Lower E with stable behavior indicates bounded dynamics.

    Args:
        vectors: List of v_native vectors.
        s: Scaling factor.
        config: Fractal configuration.

    Returns:
        Energy E (non-negative).
    """
    if not vectors:
        return 0.0

    norms = [math.sqrt(sum(v * v for v in vec)) for vec in vectors]
    mean_norm = sum(norms) / len(norms)

    # Scale by s for boundedness relation
    E = mean_norm * s

    return _quantize(max(0.0, E), config.precision_decimals)


# =============================================================================
# Diagnostics Hash
# =============================================================================


def compute_diagnostics_hash(diagnostics: FractalDiagnostics) -> str:
    """Compute SHA256 hash of diagnostics (canonical JSON).

    Args:
        diagnostics: FractalDiagnostics instance.

    Returns:
        SHA256 hex string.
    """
    canonical = diagnostics.to_canonical_dict()
    json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


# =============================================================================
# Main Computation
# =============================================================================


def compute_diagnostics(
    graph_id: str,
    vectors: List[List[float]],
    residuals: List[float],
    edge_count: int,
    graph_version: int,
    region_id: str = "global",
    config: FractalConfig = DEFAULT_CONFIG,
    similarities: Optional[List[float]] = None,
    distances: Optional[List[float]] = None,
) -> FractalDiagnostics:
    """Compute full fractal diagnostics for a graph/region.

    Args:
        graph_id: Graph identifier.
        vectors: List of v_native vectors.
        residuals: List of node residuals.
        edge_count: Number of edges.
        graph_version: Current graph version.
        region_id: Region identifier.
        config: Fractal configuration.
        similarities: Optional precomputed pairwise similarity values in stable
            i < j order (vectorized callers may pass these to skip the
            quadratic Python loop).
        distances: Optional precomputed pairwise (1 - similarity) values.

    Returns:
        FractalDiagnostics with all metrics.
    """
    n = len(vectors)

    if similarities is None:
        similarities = []
        for i in range(n):
            for j in range(i + 1, n):
                sim = _cosine_similarity(vectors[i], vectors[j])
                similarities.append(sim)

    if distances is None:
        distances = [1.0 - s for s in similarities]

    # Compute s
    s = compute_scaling_s(config)

    # Compute D
    D_hat = estimate_D_fractal(
        vectors, config.epsilons, config, distances=distances
    )

    # Compute H
    H_hat = estimate_H_entropy(similarities, config.bins, config)

    # Compute R
    redundancy_R = compute_redundancy_R(similarities, threshold=0.9, config=config)

    # Compute N
    novelty_N = compute_novelty_N(residuals, config)

    # Compute λ
    lambda_hat = estimate_lambda(novelty_N, redundancy_R, H_hat, config)

    # Compute E
    energy_E = compute_energy_E(vectors, s, config)

    # Create diagnostics (without hash first)
    diagnostics = FractalDiagnostics(
        graph_id=graph_id,
        region_id=region_id,
        node_count=n,
        edge_count=edge_count,
        s=s,
        D_hat=D_hat,
        H_hat=H_hat,
        lambda_hat=lambda_hat,
        redundancy_R=redundancy_R,
        novelty_N=novelty_N,
        energy_E=energy_E,
        computed_at_version=graph_version,
        diagnostics_hash="",
    )

    # Compute hash
    diag_hash = compute_diagnostics_hash(diagnostics)

    # Return with hash
    return FractalDiagnostics(
        graph_id=diagnostics.graph_id,
        region_id=diagnostics.region_id,
        node_count=diagnostics.node_count,
        edge_count=diagnostics.edge_count,
        s=diagnostics.s,
        D_hat=diagnostics.D_hat,
        H_hat=diagnostics.H_hat,
        lambda_hat=diagnostics.lambda_hat,
        redundancy_R=diagnostics.redundancy_R,
        novelty_N=diagnostics.novelty_N,
        energy_E=diagnostics.energy_E,
        computed_at_version=diagnostics.computed_at_version,
        diagnostics_hash=diag_hash,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "PHI",
    "GOLDEN_S",
    "PRECISION_DECIMALS",
    # Config
    "FractalConfig",
    "DEFAULT_CONFIG",
    # Result
    "FractalDiagnostics",
    # Estimators
    "compute_scaling_s",
    "estimate_D_fractal",
    "estimate_H_entropy",
    "compute_redundancy_R",
    "compute_novelty_N",
    "estimate_lambda",
    "compute_energy_E",
    # Hash
    "compute_diagnostics_hash",
    # Main
    "compute_diagnostics",
]
