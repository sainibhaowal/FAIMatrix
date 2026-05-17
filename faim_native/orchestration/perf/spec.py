"""FAIM-Native Orchestration: Performance Spec.

Defines SpeedBudget profiles with correct vector dimension (256).

Key changes for Stage-5:
- default_embedding_dim = 256 (from encoding.vector_schema)
- psutil is OPTIONAL (fallback if missing)
- FAIM_PROFILE mapping: STRICT → no GPU
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

# Import vector dimension from encoding schema
try:
    from encoding.vector_schema import VECTOR_DIMENSION
except ImportError:
    # Fallback if encoding not available
    VECTOR_DIMENSION = 256

# psutil is OPTIONAL
try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore
    _PSUTIL_AVAILABLE = False


# =============================================================================
# Enums
# =============================================================================


class PersistMode(Enum):
    """Durability strategy for writes."""

    RELAXED = "relaxed"
    STRICT = "strict"


class WritebackMode(Enum):
    """Writeback approval mode for Cortex memory consolidation."""

    MANUAL = "manual"  # All candidates require human approval (default)
    SEMI_AUTO = "semi_auto"  # Auto-approve high confidence, manual for contradictions
    AUTO = "auto"  # Auto-approve all (except explicit contradictions)


@dataclass(frozen=True)
class WritebackConfig:
    """Configuration for Cortex writeback behavior.

    Controls when and how memory candidates are persisted to the graph.
    All values can be overridden via environment variables for production flexibility.
    """

    mode: WritebackMode = WritebackMode.SEMI_AUTO

    # Confidence threshold for auto-approval (0.0 - 1.0)
    # Candidates above this threshold are auto-approved (in SEMI_AUTO mode)
    auto_approve_threshold: float = 0.90

    # Whether to require manual approval for candidates with contradictions
    require_manual_for_contradictions: bool = True

    # Maximum number of candidates to auto-approve per turn (safety limit)
    max_auto_approve_per_turn: int = 3

    # Minimum candidate confidence to even be considered (filtering threshold)
    min_candidate_confidence: float = 0.50

    @classmethod
    def from_env(cls) -> "WritebackConfig":
        """Build config from environment variables with safe defaults."""
        mode_str = os.getenv("FAIM_WRITEBACK_MODE", "semi_auto").lower()

        mode_map = {
            "manual": WritebackMode.MANUAL,
            "semi_auto": WritebackMode.SEMI_AUTO,
            "auto": WritebackMode.AUTO,
        }

        # Parse threshold with bounds checking
        try:
            threshold = float(os.getenv("FAIM_WRITEBACK_AUTO_THRESHOLD", "0.90"))
            threshold = max(0.0, min(1.0, threshold))  # Clamp to [0, 1]
        except ValueError:
            threshold = 0.90

        return cls(
            mode=mode_map.get(mode_str, WritebackMode.SEMI_AUTO),
            auto_approve_threshold=threshold,
            require_manual_for_contradictions=os.getenv(
                "FAIM_WRITEBACK_REQUIRE_MANUAL_CONTRADICTION", "true"
            ).lower()
            != "false",
            max_auto_approve_per_turn=int(os.getenv("FAIM_WRITEBACK_MAX_AUTO", "3")),
            min_candidate_confidence=float(
                os.getenv("FAIM_WRITEBACK_MIN_CONFIDENCE", "0.50")
            ),
        )


class FaimSpeedProfile(str, Enum):
    """Named speed profiles."""

    STRICT = "STRICT"  # Deterministic, no GPU, exact algorithms
    FAST = "FAST"  # May use GPU, approximate algorithms
    RELAXED = "RELAXED"  # Most permissive
    CORE_DEV = "CORE_DEV"  # Development, local experiments
    CORE_REALTIME = "CORE_REALTIME"  # Real-time agents
    CORE_SCALE = "CORE_SCALE"  # High-performance
    CORE_HARDENED = "CORE_HARDENED"  # Strict durability
    AUTO = "AUTO"  # Auto-detected
    DEFAULT = "DEFAULT"  # Default profile


# =============================================================================
# SpeedBudget Dataclass
# =============================================================================


@dataclass(frozen=True)
class SpeedBudget:
    """Immutable speed/memory budget for a FAIM deployment profile.

    All time values are milliseconds, counts are integer limits.
    """

    profile: FaimSpeedProfile

    # Insert throughput and latency
    min_insert_qps: int
    p95_insert_ms_relaxed: float
    p95_insert_ms_strict: float

    # Capacity constraints
    max_graphs: int
    max_nodes_total: int
    max_nodes_per_graph: int

    # Memory ceilings
    hot_ram_bytes: int
    max_warm_nodes: int

    # Latency targets for retrieve
    p95_retrieve_ms_1m: float
    p95_retrieve_ms_10m: float
    p99_retrieve_ms_global: Optional[float] = None

    # Persistence and hardware hints
    default_persist_mode: PersistMode = PersistMode.RELAXED
    allow_gpu: bool = True

    # Vector dimension - MUST match encoding.vector_schema.VECTOR_DIMENSION
    default_embedding_dim: int = VECTOR_DIMENSION

    # Write-behind queue budget
    write_queue_maxsize: int = 4096

    @property
    def dim(self) -> int:
        """Primary embedding dimension. Always 256 for FAIM-native."""
        return self.default_embedding_dim

    def approx_vector_ram_gib(self, nodes: int) -> float:
        """Approximate GiB of RAM for 'nodes' vectors at float32."""
        bytes_total = nodes * self.default_embedding_dim * 4
        return bytes_total / (1024**3)


# =============================================================================
# Predefined Profiles
# =============================================================================

_GIB = 1024**3

SPEED_PROFILES: Dict[FaimSpeedProfile, SpeedBudget] = {
    # STRICT: Deterministic, no GPU, exact algorithms
    FaimSpeedProfile.STRICT: SpeedBudget(
        profile=FaimSpeedProfile.STRICT,
        max_graphs=16,
        max_nodes_total=1_000_000,
        max_nodes_per_graph=500_000,
        hot_ram_bytes=2 * _GIB,
        max_warm_nodes=50_000,
        p95_retrieve_ms_1m=10.0,
        p95_retrieve_ms_10m=50.0,
        p99_retrieve_ms_global=100.0,
        min_insert_qps=50,
        p95_insert_ms_relaxed=10.0,
        p95_insert_ms_strict=25.0,
        default_persist_mode=PersistMode.STRICT,
        allow_gpu=False,  # NO GPU in STRICT mode!
    ),
    # FAST: May use GPU, approximate algorithms
    FaimSpeedProfile.FAST: SpeedBudget(
        profile=FaimSpeedProfile.FAST,
        max_graphs=8,
        max_nodes_total=10_000_000,
        max_nodes_per_graph=5_000_000,
        hot_ram_bytes=8 * _GIB,
        max_warm_nodes=200_000,
        p95_retrieve_ms_1m=2.0,
        p95_retrieve_ms_10m=10.0,
        p99_retrieve_ms_global=25.0,
        min_insert_qps=200,
        p95_insert_ms_relaxed=5.0,
        p95_insert_ms_strict=15.0,
        default_persist_mode=PersistMode.RELAXED,
        allow_gpu=True,
    ),
    # RELAXED: Most permissive
    FaimSpeedProfile.RELAXED: SpeedBudget(
        profile=FaimSpeedProfile.RELAXED,
        max_graphs=32,
        max_nodes_total=50_000_000,
        max_nodes_per_graph=10_000_000,
        hot_ram_bytes=16 * _GIB,
        max_warm_nodes=500_000,
        p95_retrieve_ms_1m=2.0,
        p95_retrieve_ms_10m=5.0,
        p99_retrieve_ms_global=20.0,
        min_insert_qps=500,
        p95_insert_ms_relaxed=3.0,
        p95_insert_ms_strict=10.0,
        default_persist_mode=PersistMode.RELAXED,
        allow_gpu=True,
    ),
    # Legacy profiles mapped to new structure
    FaimSpeedProfile.CORE_DEV: SpeedBudget(
        profile=FaimSpeedProfile.CORE_DEV,
        max_graphs=16,
        max_nodes_total=1_000_000,
        max_nodes_per_graph=500_000,
        hot_ram_bytes=2 * _GIB,
        max_warm_nodes=50_000,
        p95_retrieve_ms_1m=5.0,
        p95_retrieve_ms_10m=20.0,
        p99_retrieve_ms_global=50.0,
        min_insert_qps=50,
        p95_insert_ms_relaxed=10.0,
        p95_insert_ms_strict=25.0,
        default_persist_mode=PersistMode.RELAXED,
        allow_gpu=False,
    ),
    FaimSpeedProfile.CORE_REALTIME: SpeedBudget(
        profile=FaimSpeedProfile.CORE_REALTIME,
        max_graphs=3,
        max_nodes_total=10_000_000,
        max_nodes_per_graph=10_000_000,
        hot_ram_bytes=6 * _GIB,
        max_warm_nodes=200_000,
        p95_retrieve_ms_1m=2.0,
        p95_retrieve_ms_10m=10.0,
        p99_retrieve_ms_global=25.0,
        min_insert_qps=100,
        p95_insert_ms_relaxed=5.0,
        p95_insert_ms_strict=20.0,
        default_persist_mode=PersistMode.RELAXED,
        allow_gpu=True,
    ),
    FaimSpeedProfile.CORE_SCALE: SpeedBudget(
        profile=FaimSpeedProfile.CORE_SCALE,
        max_graphs=8,
        max_nodes_total=80_000_000,
        max_nodes_per_graph=20_000_000,
        hot_ram_bytes=64 * _GIB,
        max_warm_nodes=1_000_000,
        p95_retrieve_ms_1m=2.0,
        p95_retrieve_ms_10m=3.0,
        p99_retrieve_ms_global=15.0,
        min_insert_qps=500,
        p95_insert_ms_relaxed=5.0,
        p95_insert_ms_strict=20.0,
        default_persist_mode=PersistMode.RELAXED,
        allow_gpu=True,
    ),
    FaimSpeedProfile.CORE_HARDENED: SpeedBudget(
        profile=FaimSpeedProfile.CORE_HARDENED,
        max_graphs=8,
        max_nodes_total=80_000_000,
        max_nodes_per_graph=20_000_000,
        hot_ram_bytes=64 * _GIB,
        max_warm_nodes=1_000_000,
        p95_retrieve_ms_1m=3.0,
        p95_retrieve_ms_10m=5.0,
        p99_retrieve_ms_global=40.0,
        min_insert_qps=200,
        p95_insert_ms_relaxed=8.0,
        p95_insert_ms_strict=20.0,
        default_persist_mode=PersistMode.STRICT,
        allow_gpu=True,
    ),
    FaimSpeedProfile.AUTO: SpeedBudget(
        profile=FaimSpeedProfile.AUTO,
        max_graphs=10,
        max_nodes_total=50_000_000,
        max_nodes_per_graph=10_000_000,
        hot_ram_bytes=16 * _GIB,
        max_warm_nodes=500_000,
        p95_retrieve_ms_1m=2.0,
        p95_retrieve_ms_10m=5.0,
        p99_retrieve_ms_global=30.0,
        min_insert_qps=100,
        p95_insert_ms_relaxed=5.0,
        p95_insert_ms_strict=20.0,
        default_persist_mode=PersistMode.RELAXED,
        allow_gpu=True,
    ),
}


# =============================================================================
# Profile Resolution
# =============================================================================


def get_speed_budget(profile: str | FaimSpeedProfile) -> SpeedBudget:
    """Resolve a profile name into a SpeedBudget.

    Args:
        profile: Profile name or enum.

    Returns:
        SpeedBudget for the profile.

    Raises:
        KeyError: If profile is unknown.
    """
    if isinstance(profile, str):
        profile_upper = profile.upper()

        # Map aliases
        if profile_upper == "DEFAULT":
            profile_upper = "STRICT"  # Default to STRICT for determinism

        try:
            profile_enum = FaimSpeedProfile(profile_upper)
        except ValueError as exc:
            raise KeyError(f"Unknown FAIM speed profile: {profile!r}") from exc
    else:
        profile_enum = profile

    # AUTO profile adapts to system
    if profile_enum == FaimSpeedProfile.AUTO:
        return adapt_speed_budget_to_system()

    return SPEED_PROFILES.get(profile_enum, SPEED_PROFILES[FaimSpeedProfile.STRICT])


def adapt_speed_budget_to_system() -> SpeedBudget:
    """Adapt SpeedBudget based on system resources.

    Uses psutil if available, otherwise returns conservative defaults.
    """
    # Default values if psutil not available
    total_ram = 8 * _GIB  # Assume 8GB

    if _PSUTIL_AVAILABLE and psutil is not None:
        try:
            total_ram = psutil.virtual_memory().total
        except Exception:  # nosec B110 - graceful fallback
            pass  # Use default

    # Compute parameters based on RAM
    hot_ram_bytes = int(total_ram * 0.6)

    if total_ram < 8 * _GIB:
        max_nodes_total = 10_000_000
        hot_ram_bytes = int(total_ram * 0.5)
    elif total_ram < 32 * _GIB:
        max_nodes_total = 20_000_000
    else:
        max_nodes_total = 50_000_000

    return SpeedBudget(
        profile=FaimSpeedProfile.AUTO,
        max_graphs=10,
        max_nodes_total=max_nodes_total,
        max_nodes_per_graph=10_000_000,
        hot_ram_bytes=hot_ram_bytes,
        max_warm_nodes=500_000,
        p95_retrieve_ms_1m=2.0,
        p95_retrieve_ms_10m=5.0,
        p99_retrieve_ms_global=30.0,
        min_insert_qps=100,
        p95_insert_ms_relaxed=5.0,
        p95_insert_ms_strict=20.0,
        default_persist_mode=PersistMode.RELAXED,
        allow_gpu=True,
    )


def get_memory_info() -> Dict[str, int]:
    """Get system memory info.

    Returns dict with 'total', 'available', 'used' in bytes.
    Returns zeros if psutil not available.
    """
    if not _PSUTIL_AVAILABLE or psutil is None:
        return {"total": 0, "available": 0, "used": 0}

    try:
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
        }
    except Exception:  # nosec B110 - graceful fallback
        return {"total": 0, "available": 0, "used": 0}


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "PersistMode",
    "WritebackMode",
    "WritebackConfig",
    "FaimSpeedProfile",
    "SpeedBudget",
    "SPEED_PROFILES",
    "get_speed_budget",
    "adapt_speed_budget_to_system",
    "get_memory_info",
    "VECTOR_DIMENSION",
]
