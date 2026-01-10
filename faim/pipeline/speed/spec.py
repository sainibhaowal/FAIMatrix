from __future__ import annotations  # __future__ import at the top (if used)

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import psutil  # Standard library imports


# Define PersistMode if it's not already defined
class PersistMode(Enum):
    """Durability strategy for writes to the cold tier (Tier-3)."""

    RELAXED = "relaxed"
    STRICT = "strict"


class FaimSpeedProfile(str, Enum):
    """Named speed profiles as described in docs/FAIM_Speed_Spec.md."""

    CORE_DEV = "CORE_DEV"  # Development, local experiments
    CORE_REALTIME = "CORE_REALTIME"  # Real-time agents, low-latency systems
    CORE_SCALE = "CORE_SCALE"  # High-performance, large-scale graphs
    CORE_HARDENED = "CORE_HARDENED"  # Strict durability, enterprise-level
    AUTO = "AUTO"  # Auto-detected profile for dynamic scaling
    DEFAULT = "DEFAULT"  # Add this line for a default profile


@dataclass(frozen=True)
class SpeedBudget:
    """
    Immutable speed/memory budget for a FAIM deployment profile.

    All time values are milliseconds, counts are integer limits, and sizes are
    expressed in bytes. These numbers are *targets* that the P4.x HyperSpeed
    backend must satisfy under realistic workloads.
    """

    profile: FaimSpeedProfile

    # Insert throughput and latency (steady state) (mandatory fields)
    min_insert_qps: int
    p95_insert_ms_relaxed: float
    p95_insert_ms_strict: float

    # Capacity constraints (mandatory fields)
    max_graphs: int
    max_nodes_total: int
    max_nodes_per_graph: int

    # Memory ceilings (Tier-1 vectors + Tier-2 cache) (mandatory fields)
    hot_ram_bytes: int
    max_warm_nodes: int

    # Latency targets (ms) for retrieve(graph_id, query, k) (mandatory fields)
    p95_retrieve_ms_1m: float
    p95_retrieve_ms_10m: float
    p99_retrieve_ms_global: Optional[float] = None

    # Persistence and hardware hints (optional fields)
    default_persist_mode: PersistMode = PersistMode.RELAXED
    allow_gpu: bool = True

    # Default embedding assumptions (for RAM planning only)
    # This is also the vector dimension used by VectorBank / GPU backend.
    default_embedding_dim: int = 64

    # Write-behind queue budget (used by P4.4 tests later)
    write_queue_maxsize: int = 4096

    @property
    def dim(self) -> int:
        """
        Primary embedding dimension. Tests require dim >= 4.
        """
        return self.default_embedding_dim

    def approx_vector_ram_gib(self, nodes: int) -> float:
        """
        Approximate GiB of RAM needed to store 'nodes' vectors of
        default_embedding_dim at float32 precision.
        """
        bytes_total = nodes * self.default_embedding_dim * 4
        return bytes_total / (1024**3)


# Helper for GiB -> bytes
_GIB = 1024**3

SPEED_PROFILES: Dict[FaimSpeedProfile, SpeedBudget] = {
    FaimSpeedProfile.CORE_DEV: SpeedBudget(
        profile=FaimSpeedProfile.CORE_DEV,
        max_graphs=16,
        max_nodes_total=1_000_000,
        max_nodes_per_graph=500_000,
        hot_ram_bytes=2 * _GIB,  # adjustable for local dev
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
    FaimSpeedProfile.AUTO: SpeedBudget(  # auto-profile for dynamic scaling
        profile=FaimSpeedProfile.AUTO,
        max_graphs=10,
        max_nodes_total=50_000_000,  # will adapt based on system resources
        max_nodes_per_graph=10_000_000,
        hot_ram_bytes=16 * _GIB,  # Dynamically adjusted based on available resources
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


def get_speed_budget(profile: str | FaimSpeedProfile) -> SpeedBudget:
    """
    Resolve a profile name (from env/config) into a SpeedBudget.
    Includes AUTO profile that dynamically detects system resources.

    Raises:
        KeyError: if the profile is unknown.
    """
    if isinstance(profile, str):
        profile = profile.upper()
        # Map "Default" to "CORE_DEV"
        if profile == "DEFAULT":
            profile = "CORE_DEV"  # or whichever profile you prefer

        try:
            profile_enum = FaimSpeedProfile(profile)
        except ValueError as exc:
            raise KeyError(f"Unknown FAIM speed profile: {profile!r}") from exc
    else:
        profile_enum = profile

    # AUTO profile adapts based on system specs, so we don’t just pull from a dict.
    if profile_enum == FaimSpeedProfile.AUTO:
        # Detect system RAM, VRAM, etc., and return an appropriately sized SpeedBudget.
        return adapt_speed_budget_to_system()

    return SPEED_PROFILES[profile_enum]


def adapt_speed_budget_to_system() -> SpeedBudget:
    """
    This function adapts the SpeedBudget for the system based on available resources.
    For example, it detects the total available RAM and adjusts the SpeedBudget accordingly.
    """
    total_ram = psutil.virtual_memory().total  # Get total RAM in bytes
    max_graphs = 10
    max_nodes_total = 50_000_000  # Default, will adapt
    max_nodes_per_graph = 10_000_000
    hot_ram_bytes = int(total_ram * 0.6)  # 60% of total RAM for hot memory
    max_warm_nodes = 500_000
    p95_retrieve_ms_1m = 2.0
    p95_retrieve_ms_10m = 5.0
    p99_retrieve_ms_global = 30.0
    min_insert_qps = 100
    p95_insert_ms_relaxed = 5.0
    p95_insert_ms_strict = 20.0
    default_persist_mode = PersistMode.RELAXED
    allow_gpu = True  # Assuming GPU is available, but we can adapt this

    # Adjust based on available RAM
    if total_ram < 8 * 1024**3:  # less than 8GB RAM, reduce node count
        max_nodes_total = 10_000_000
        hot_ram_bytes = int(total_ram * 0.5)  # Use 50% of RAM
    elif total_ram < 32 * 1024**3:  # between 8GB and 32GB
        max_nodes_total = 20_000_000

    return SpeedBudget(
        profile=FaimSpeedProfile.AUTO,
        max_graphs=max_graphs,
        max_nodes_total=max_nodes_total,
        max_nodes_per_graph=max_nodes_per_graph,
        hot_ram_bytes=hot_ram_bytes,
        max_warm_nodes=max_warm_nodes,
        p95_retrieve_ms_1m=p95_retrieve_ms_1m,
        p95_retrieve_ms_10m=p95_retrieve_ms_10m,
        p99_retrieve_ms_global=p99_retrieve_ms_global,
        min_insert_qps=min_insert_qps,
        p95_insert_ms_relaxed=p95_insert_ms_relaxed,
        p95_insert_ms_strict=p95_insert_ms_strict,
        default_persist_mode=default_persist_mode,
        allow_gpu=allow_gpu,
    )
