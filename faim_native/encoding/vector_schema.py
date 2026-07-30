"""FAIMVector v1 Schema - Frozen Immutable Contract.

This module defines the core FAIM-native vector schema.
All vectors are deterministic - same input produces same output.

Schema Version: v1

NO ML MODELS. NO RANDOMNESS.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import BlockAnchor, uuid7
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import BlockAnchor, uuid7


# Schema constants
SCHEMA_VERSION = "v1"
VECTOR_DIMENSION = 256  # Fixed dimension for v1


# -----------------------------------------------------------------------------
# FAIMVector - Frozen Immutable Vector Contract
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FAIMVector:
    """FAIM-native vector representation.

    This is the atomic unit of FAIM memory. Each vector is:
    - Deterministic (same input → same v_native and vector_hash)
    - Immutable (frozen dataclass)
    - Self-describing (includes schema_version and provenance)

    Attributes:
        id: UUID7 identifier.
        schema_version: Always "v1" for this implementation.
        raw_id: Reference to source RawRef.
        block_id: Reference to source EvidenceBlock.
        block_type: Type from EvidenceBlock ("text", "table", etc).
        anchor_dict: BlockAnchor as dictionary.
        v_native: Fixed-dimension vector (256 floats).
        parents: Parent vector IDs (empty for atoms, filled in Stage-4).
        fractions: Weights for parent contributions (empty for atoms).
        residual: Novelty proxy (0.0-1.0).
        opp_signature: Numeric signature for antisym opposition.
        level: Hierarchy level (0 for atoms).
        usage: Usage tracking {touch_count, last_access}.
        provenance: Source metadata {raw_id, anchor, extractor, confidence}.
        vector_hash: SHA256 of canonical JSON (excludes usage).
    """

    id: UUID
    schema_version: str
    raw_id: str
    block_id: str
    block_type: str
    anchor_dict: Dict[str, Any]
    v_native: Tuple[float, ...]
    parents: Tuple[str, ...]
    fractions: Tuple[float, ...]
    residual: float
    opp_signature: Dict[str, float]
    level: int
    usage: Dict[str, int]
    provenance: Dict[str, Any]
    vector_hash: str

    @classmethod
    def create(
        cls,
        raw_id: str,
        block_id: str,
        block_type: str,
        anchor: BlockAnchor,
        v_native: list[float],
        opp_signature: Dict[str, float],
        residual: float = 0.0,
        parents: Optional[list[str]] = None,
        fractions: Optional[list[float]] = None,
        level: int = 0,
        extractor: str = "faim_native",
        confidence: float = 1.0,
    ) -> "FAIMVector":
        """Create a new FAIMVector with computed hash.

        Args:
            raw_id: Reference to source RawRef.
            block_id: Reference to source EvidenceBlock.
            block_type: Type of block.
            anchor: BlockAnchor from block.
            v_native: Vector values (must be VECTOR_DIMENSION length).
            opp_signature: Opposition signature dict.
            residual: Novelty proxy.
            parents: Parent vector IDs.
            fractions: Parent weights.
            level: Hierarchy level.
            extractor: Extractor name.
            confidence: Extraction confidence.

        Returns:
            FAIMVector with computed vector_hash.
        """
        assert (  # nosec B101
            len(v_native) == VECTOR_DIMENSION
        ), f"v_native must be {VECTOR_DIMENSION} dims, got {len(v_native)}"

        anchor_dict = anchor.to_dict()
        parents_tuple = tuple(parents or [])
        fractions_tuple = tuple(fractions or [])
        v_native_tuple = tuple(v_native)

        now = datetime.now(timezone.utc)
        usage = {
            "touch_count": 0,
            "last_access": int(now.timestamp()),
        }

        provenance = {
            "raw_id": raw_id,
            "anchor": anchor_dict,
            "extractor": extractor,
            "confidence": confidence,
        }

        # Build temporary object to compute hash
        temp_id = uuid7()

        # Compute vector_hash from canonical representation (excludes usage and id)
        canonical = _build_canonical_dict(
            schema_version=SCHEMA_VERSION,
            raw_id=raw_id,
            block_id=block_id,
            block_type=block_type,
            anchor_dict=anchor_dict,
            v_native=v_native_tuple,
            parents=parents_tuple,
            fractions=fractions_tuple,
            residual=residual,
            opp_signature=opp_signature,
            level=level,
            provenance=provenance,
        )
        vector_hash = _compute_hash(canonical)

        return cls(
            id=temp_id,
            schema_version=SCHEMA_VERSION,
            raw_id=raw_id,
            block_id=block_id,
            block_type=block_type,
            anchor_dict=anchor_dict,
            v_native=v_native_tuple,
            parents=parents_tuple,
            fractions=fractions_tuple,
            residual=residual,
            opp_signature=opp_signature,
            level=level,
            usage=usage,
            provenance=provenance,
            vector_hash=vector_hash,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "schema_version": self.schema_version,
            "raw_id": self.raw_id,
            "block_id": self.block_id,
            "block_type": self.block_type,
            "anchor_dict": self.anchor_dict,
            "v_native": list(self.v_native),
            "parents": list(self.parents),
            "fractions": list(self.fractions),
            "residual": self.residual,
            "opp_signature": self.opp_signature,
            "level": self.level,
            "usage": self.usage,
            "provenance": self.provenance,
            "vector_hash": self.vector_hash,
        }

    def to_canonical_dict(self) -> Dict[str, Any]:
        """Convert to canonical dict for hashing (excludes usage and id)."""
        return _build_canonical_dict(
            schema_version=self.schema_version,
            raw_id=self.raw_id,
            block_id=self.block_id,
            block_type=self.block_type,
            anchor_dict=self.anchor_dict,
            v_native=self.v_native,
            parents=self.parents,
            fractions=self.fractions,
            residual=self.residual,
            opp_signature=self.opp_signature,
            level=self.level,
            provenance=self.provenance,
        )

    def verify_hash(self) -> bool:
        """Verify the vector_hash matches computed value."""
        canonical = self.to_canonical_dict()
        expected = _compute_hash(canonical)
        return self.vector_hash == expected

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FAIMVector":
        """Reconstruct from dictionary."""
        return cls(
            id=UUID(data["id"]),
            schema_version=data["schema_version"],
            raw_id=data["raw_id"],
            block_id=data["block_id"],
            block_type=data["block_type"],
            anchor_dict=data["anchor_dict"],
            v_native=tuple(data["v_native"]),
            parents=tuple(data["parents"]),
            fractions=tuple(data["fractions"]),
            residual=data["residual"],
            opp_signature=data["opp_signature"],
            level=data["level"],
            usage=data["usage"],
            provenance=data["provenance"],
            vector_hash=data["vector_hash"],
        )


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------


def _build_canonical_dict(
    schema_version: str,
    raw_id: str,
    block_id: str,
    block_type: str,
    anchor_dict: Dict[str, Any],
    v_native: Tuple[float, ...],
    parents: Tuple[str, ...],
    fractions: Tuple[float, ...],
    residual: float,
    opp_signature: Dict[str, float],
    level: int,
    provenance: Dict[str, Any],
) -> Dict[str, Any]:
    """Build canonical dict with deterministic key ordering."""
    return {
        "anchor_dict": anchor_dict,
        "block_id": block_id,
        "block_type": block_type,
        "fractions": list(fractions),
        "level": level,
        "opp_signature": dict(sorted(opp_signature.items())),
        "parents": list(parents),
        "provenance": dict(sorted(provenance.items(), key=lambda x: x[0])),
        "raw_id": raw_id,
        "residual": round(residual, 10),  # Round to avoid float precision issues
        "schema_version": schema_version,
        "v_native": [round(v, 10) for v in v_native],  # Round for determinism
    }


def _compute_hash(canonical: Dict[str, Any]) -> str:
    """Compute SHA256 hash of canonical JSON."""
    json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def compute_vector_hash(vector: FAIMVector) -> str:
    """Compute hash for a vector (for external use)."""
    canonical = vector.to_canonical_dict()
    return _compute_hash(canonical)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    "SCHEMA_VERSION",
    "VECTOR_DIMENSION",
    "FAIMVector",
    "compute_vector_hash",
]
