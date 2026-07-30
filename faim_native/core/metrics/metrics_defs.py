"""FAIM-Native Metrics Contract.

Contract-only definitions for metrics - NO COMPUTATION.
All computation is in fractal_physics.py.

This file defines:
- MetricKey constants (stable ordering)
- MetricsSnapshot dataclass (UI/API schema)
- validate_metric_payload (pure checks)

NO NUMPY. NO COMPUTATION. CONTRACTS ONLY.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# =============================================================================
# Metric Key Constants (Stable Ordering)
# =============================================================================


class MetricKey:
    """Metric key constants for FAIM-native diagnostics.

    These are the canonical keys used in MetricsSnapshot.metrics dict.
    Order is stable for deterministic hashing.
    """

    CR = "CR"  # Compression ratio
    R = "R"  # Redundancy
    D_HAT = "D_hat"  # Fractal dimension estimate
    H_HAT = "H_hat"  # Entropy/disorder estimate
    LAMBDA_HAT = "lambda_hat"  # Evolution pressure
    NOVELTY = "novelty"  # Novelty measure
    ENERGY = "energy"  # Energy/boundedness


# Ordered list for stable iteration (alphabetical by key)
METRIC_KEYS_ORDERED: List[str] = [
    MetricKey.CR,
    MetricKey.D_HAT,
    MetricKey.ENERGY,
    MetricKey.H_HAT,
    MetricKey.LAMBDA_HAT,
    MetricKey.NOVELTY,
    MetricKey.R,
]


# =============================================================================
# MetricsSnapshot Dataclass (UI/API Schema)
# =============================================================================


@dataclass(frozen=True)
class MetricsSnapshot:
    """Canonical metrics payload for UI and API.

    This is the ONLY format returned by:
    - events: DIAGNOSTICS_SNAPSHOT
    - endpoint: /metrics/scorecard

    Attributes:
        graph_id: Graph identifier.
        graph_version: Version at time of computation.
        graph_hash: Hash of graph state.
        metrics: Dict of metric values (keys from METRIC_KEYS_ORDERED).
        diagnostics_hash: SHA256 of canonical metrics (stable).
        created_at: When computed (optional, NEVER used in hashes).
    """

    graph_id: str
    graph_version: int
    graph_hash: str
    metrics: Dict[str, float]
    diagnostics_hash: str
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization.

        Note: created_at is excluded from hash computation.
        """
        return {
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "graph_hash": self.graph_hash,
            "metrics": self.metrics,
            "diagnostics_hash": self.diagnostics_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Convert to canonical dict for hashing (stable ordering).

        Excludes created_at (volatile).
        """
        return {
            "graph_hash": self.graph_hash,
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "metrics": {k: self.metrics.get(k, 0.0) for k in METRIC_KEYS_ORDERED},
        }

    def to_event_payload(self) -> Dict[str, Any]:
        """Convert to event payload format.

        Flattens metrics into top-level keys for DIAGNOSTICS_SNAPSHOT.
        """
        payload = {
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "graph_hash": self.graph_hash,
            "diagnostics_hash": self.diagnostics_hash,
        }
        # Add individual metrics
        for k, v in self.metrics.items():
            payload[k] = v
        return payload


# =============================================================================
# Validation
# =============================================================================


def validate_metric_payload(payload: Dict[str, Any]) -> List[str]:
    """Validate a metric payload against the contract.

    Returns list of error messages. Empty list = valid.

    Checks:
    - Required fields present
    - Metric values are numeric
    - Metric values are in valid ranges

    Args:
        payload: Dict to validate.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    # Required fields
    required = ["graph_id", "graph_version", "diagnostics_hash"]
    for field_name in required:
        if field_name not in payload:
            errors.append(f"Missing required field: {field_name}")

    # Either "metrics" dict or flat metric keys
    has_metrics_dict = "metrics" in payload and isinstance(payload["metrics"], dict)

    if has_metrics_dict:
        metrics = payload["metrics"]
    else:
        # Check for flat metric keys
        metrics = {k: payload.get(k) for k in METRIC_KEYS_ORDERED if k in payload}

    # Validate metric values
    for key in METRIC_KEYS_ORDERED:
        if key in metrics:
            value = metrics[key]
            if not isinstance(value, (int, float)):
                errors.append(
                    f"Metric {key} must be numeric, got {type(value).__name__}"
                )
            elif value != value:  # NaN check
                errors.append(f"Metric {key} is NaN")

    # Range checks
    range_checks = {
        MetricKey.R: (0.0, 1.0),
        MetricKey.H_HAT: (0.0, 1.0),
        MetricKey.LAMBDA_HAT: (0.0, 1.0),
        MetricKey.NOVELTY: (0.0, 1.0),
    }

    for key, (min_val, max_val) in range_checks.items():
        if key in metrics:
            value = metrics[key]
            if isinstance(value, (int, float)) and (value < min_val or value > max_val):
                errors.append(
                    f"Metric {key}={value} out of range [{min_val}, {max_val}]"
                )

    # D_hat non-negative
    if MetricKey.D_HAT in metrics:
        d_hat = metrics[MetricKey.D_HAT]
        if isinstance(d_hat, (int, float)) and d_hat < 0:
            errors.append(f"Metric D_hat={d_hat} must be non-negative")

    # Energy non-negative
    if MetricKey.ENERGY in metrics:
        energy = metrics[MetricKey.ENERGY]
        if isinstance(energy, (int, float)) and energy < 0:
            errors.append(f"Metric energy={energy} must be non-negative")

    return errors


def compute_snapshot_hash(snapshot: MetricsSnapshot) -> str:
    """Compute SHA256 hash of MetricsSnapshot canonical form.

    Args:
        snapshot: MetricsSnapshot to hash.

    Returns:
        SHA256 hex string.
    """
    canonical = snapshot.to_canonical_dict()
    json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def create_metrics_snapshot(
    graph_id: str,
    graph_version: int,
    graph_hash: str,
    metrics: Dict[str, float],
    created_at: Optional[datetime] = None,
) -> MetricsSnapshot:
    """Factory function to create MetricsSnapshot with computed hash.

    Args:
        graph_id: Graph identifier.
        graph_version: Graph version.
        graph_hash: Hash of graph state.
        metrics: Dict of metric values.
        created_at: Optional creation time.

    Returns:
        MetricsSnapshot with diagnostics_hash computed.
    """
    # Create without hash first
    temp = MetricsSnapshot(
        graph_id=graph_id,
        graph_version=graph_version,
        graph_hash=graph_hash,
        metrics=metrics,
        diagnostics_hash="",
        created_at=created_at,
    )

    # Compute hash
    diag_hash = compute_snapshot_hash(temp)

    # Return with hash
    return MetricsSnapshot(
        graph_id=graph_id,
        graph_version=graph_version,
        graph_hash=graph_hash,
        metrics=metrics,
        diagnostics_hash=diag_hash,
        created_at=created_at,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "MetricKey",
    "METRIC_KEYS_ORDERED",
    # Schema
    "MetricsSnapshot",
    # Validation
    "validate_metric_payload",
    "compute_snapshot_hash",
    "create_metrics_snapshot",
]
