"""FAIM-Native Index Collections Schema.

Defines collection naming and schema for Qdrant vector index.

Key properties:
- Collection naming: faim_<tenant_or_project_id>
- Payload fields: graph_id, node_id, level, kind
- Cosine distance, size=256 (from encoding.vector_schema)
- NO numpy, NO ML dependencies
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID

# Import vector dimension from encoding schema (single source of truth)
try:
    from encoding.vector_schema import VECTOR_DIMENSION
except ImportError:
    VECTOR_DIMENSION = 256  # Fallback


# =============================================================================
# Constants
# =============================================================================

# Collection prefix
COLLECTION_PREFIX = "faim_"

# Payload field names
FIELD_GRAPH_ID = "graph_id"
FIELD_NODE_ID = "node_id"
FIELD_LEVEL = "level"
FIELD_KIND = "kind"

# Required payload fields
REQUIRED_PAYLOAD_FIELDS = [FIELD_GRAPH_ID, FIELD_NODE_ID]
OPTIONAL_PAYLOAD_FIELDS = [FIELD_LEVEL, FIELD_KIND]


# =============================================================================
# Collection Schema
# =============================================================================


@dataclass(frozen=True)
class CollectionSchema:
    """Schema definition for a FAIM vector collection.

    Attributes:
        name: Collection name (faim_<tenant_id>)
        dimension: Vector dimension (always 256)
        distance: Distance metric (always cosine)
        payload_fields: Required payload field names
    """

    name: str
    dimension: int = VECTOR_DIMENSION
    distance: str = "cosine"
    payload_fields: List[str] = None

    def __post_init__(self) -> None:
        if self.payload_fields is None:
            object.__setattr__(
                self,
                "payload_fields",
                REQUIRED_PAYLOAD_FIELDS + OPTIONAL_PAYLOAD_FIELDS,
            )

    def to_qdrant_config(self) -> Dict:
        """Convert to Qdrant VectorParams config dict."""
        return {
            "size": self.dimension,
            "distance": self.distance.upper(),
        }


# =============================================================================
# Collection Naming
# =============================================================================


def collection_name(project_id: UUID) -> str:
    """Generate collection name for a project/tenant.

    Format: faim_<project_id_without_dashes>

    Args:
        project_id: Project/tenant UUID.

    Returns:
        Collection name string.
    """
    return f"{COLLECTION_PREFIX}{str(project_id).replace('-', '_')}"


def parse_collection_name(name: str) -> Optional[str]:
    """Parse project ID from collection name.

    Args:
        name: Collection name.

    Returns:
        Project ID string (with underscores), or None if not a FAIM collection.
    """
    if not name.startswith(COLLECTION_PREFIX):
        return None
    return name[len(COLLECTION_PREFIX) :]


# =============================================================================
# Point ID Generation (Deterministic)
# =============================================================================


def point_id_from_node_id(node_id: str) -> str:
    """Generate deterministic point ID from node_id.

    Uses the node_id directly as the point ID (Qdrant supports string UUIDs).

    DO NOT use Python hash() - it's not deterministic across runs!

    Args:
        node_id: Node UUID string.

    Returns:
        Point ID string (same as node_id for simplicity).
    """
    # Qdrant accepts UUID strings directly
    return node_id


def point_id_from_uuid(node_uuid: UUID) -> str:
    """Generate deterministic point ID from node UUID.

    Args:
        node_uuid: Node UUID.

    Returns:
        Point ID string.
    """
    return str(node_uuid)


# =============================================================================
# Schema Validation
# =============================================================================


def validate_payload(payload: Dict) -> List[str]:
    """Validate payload against schema.

    Args:
        payload: Payload dict to validate.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    for field in REQUIRED_PAYLOAD_FIELDS:
        if field not in payload:
            errors.append(f"Missing required field: {field}")

    return errors


def create_payload(
    graph_id: str,
    node_id: str,
    level: int = 0,
    kind: str = "atom",
) -> Dict:
    """Create a valid payload dict.

    Args:
        graph_id: Graph identifier.
        node_id: Node identifier.
        level: Node level in hierarchy (default 0).
        kind: Node kind ("atom" or "macro").

    Returns:
        Payload dict.
    """
    return {
        FIELD_GRAPH_ID: str(graph_id),
        FIELD_NODE_ID: str(node_id),
        FIELD_LEVEL: level,
        FIELD_KIND: kind,
    }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "VECTOR_DIMENSION",
    "COLLECTION_PREFIX",
    "FIELD_GRAPH_ID",
    "FIELD_NODE_ID",
    "FIELD_LEVEL",
    "FIELD_KIND",
    "CollectionSchema",
    "collection_name",
    "parse_collection_name",
    "point_id_from_node_id",
    "point_id_from_uuid",
    "validate_payload",
    "create_payload",
]
