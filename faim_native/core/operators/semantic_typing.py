"""Semantic Edge Typing and Weighting (Phase 8).

Deterministic, vector-only semantic relationship classification for inheritance edges.
Classifies edge relationships into SYNONYM, HYPERNYM, HYPONYM, RELATED based on
cosine similarity and node level (no ML, no embeddings, no text).

Two-layer strategy:
- Layer A: meta field on inheritance edges {"semantic_type": str, "semantic_weight": float}
- Layer B: separate edge rows with kind="synonym"/"hypernym"/"hyponym"/"related"
"""

from typing import Any, Dict, Optional

# =============================================================================
# Constants
# =============================================================================

SEMANTIC_WEIGHTS: Dict[str, float] = {
    "synonym": 0.95,
    "hypernym": 0.80,
    "hyponym": 0.75,
    "related": 0.60,
    "distributional_synonym": 0.78,
    "paraphrase": 0.74,
    "concept_surface": 0.70,
    "translation": 0.72,
    "entity_alias": 0.90,
    "relation_alias": 0.86,
    "entity_relation": 0.88,
    "fact_value": 0.84,
    "fact_time": 0.82,
    "domain_term": 0.68,
    "kb_source": 0.58,
    "standard": 1.00,  # no semantic modifier
}

# Cosine similarity thresholds for classification (checked in order)
SYNONYM_COSINE_THRESHOLD = 0.93  # cosine >= 0.93 → synonym
HYPERNYM_COSINE_THRESHOLD = 0.82  # cosine >= 0.82 → hypernym/hyponym (based on level)
RELATED_COSINE_THRESHOLD = 0.65  # cosine >= 0.65 → related
# cosine < 0.65 → standard (no semantic label)

# Known semantic edge kinds (Layer B edges use these as the `kind` column value)
KNOWN_SEMANTIC_KINDS: frozenset = frozenset(
    {
        "synonym",
        "hypernym",
        "hyponym",
        "related",
        "distributional_synonym",
        "paraphrase",
        "concept_surface",
        "translation",
        "entity_alias",
        "relation_alias",
        "entity_relation",
        "fact_value",
        "fact_time",
        "domain_term",
        "kb_source",
    }
)

# All valid edge kinds in FAIM (inheritance + opposition + semantic)
ALL_EDGE_KINDS: frozenset = frozenset(
    {
        "inheritance",
        "opposition",
        "synonym",
        "hypernym",
        "hyponym",
        "related",
        "distributional_synonym",
        "paraphrase",
        "concept_surface",
        "translation",
        "entity_alias",
        "relation_alias",
        "entity_relation",
        "fact_value",
        "fact_time",
        "domain_term",
        "kb_source",
    }
)


# =============================================================================
# Semantic Type Classification
# =============================================================================


def classify_semantic_type(
    cosine_sim: float,
    child_level: int,
    parent_level: int,
) -> str:
    """Classify semantic relationship type from cosine similarity and node levels.

    Uses deterministic thresholds based on vector cosine and FIG level hierarchy.
    No ML, no text, purely geometric + structural.

    Args:
        cosine_sim: Cosine similarity between child and parent vectors (0-1)
        child_level: Child node level in FIG hierarchy (typically 0 for atoms)
        parent_level: Parent node level in FIG hierarchy

    Returns:
        str: One of "synonym", "hypernym", "hyponym", "related", "standard"
    """
    if cosine_sim >= SYNONYM_COSINE_THRESHOLD:
        # Very high similarity → synonym
        return "synonym"

    if cosine_sim >= HYPERNYM_COSINE_THRESHOLD:
        # High similarity; decide based on level
        if parent_level > child_level:
            # Parent is at higher (more abstract) level → generalization → hypernym
            return "hypernym"
        elif parent_level < child_level:
            # Parent is at lower (more specific) level → specialization → hyponym
            return "hyponym"
        else:
            # Same level; tie-break: assume generalization (hypernym)
            return "hypernym"

    if cosine_sim >= RELATED_COSINE_THRESHOLD:
        # Moderate similarity → related
        return "related"

    # Low similarity → no semantic type
    return "standard"


# =============================================================================
# Meta Field Building
# =============================================================================


def build_semantic_meta(semantic_type: str) -> Dict[str, Any]:
    """Build the meta dict to store on an edge (Layer A).

    Args:
        semantic_type: One of SEMANTIC_WEIGHTS keys

    Returns:
        dict: {"semantic_type": str, "semantic_weight": float}
    """
    if semantic_type not in SEMANTIC_WEIGHTS:
        semantic_type = "standard"

    return {
        "semantic_type": semantic_type,
        "semantic_weight": SEMANTIC_WEIGHTS[semantic_type],
    }


def get_semantic_weight_from_meta(meta: Optional[Dict]) -> float:
    """Extract semantic_weight from edge meta, with safe fallback.

    Args:
        meta: Edge meta JSONB dict or None

    Returns:
        float: semantic_weight from meta, or 1.0 if unavailable
    """
    if not meta or not isinstance(meta, dict):
        return 1.0
    return float(meta.get("semantic_weight", 1.0))


# =============================================================================
# Layer B Decision
# =============================================================================


def should_create_semantic_edge(semantic_type: str) -> bool:
    """Return True iff this type warrants a Layer B edge row.

    Layer B edges are separate edge table rows with kind=semantic_type.
    "standard" type edges are not created as Layer B (only Layer A meta).

    Args:
        semantic_type: One of classify_semantic_type() return values

    Returns:
        bool: True if Layer B edge should be created
    """
    return semantic_type in KNOWN_SEMANTIC_KINDS
