"""Phase 8: Semantic Edge Typing unit tests.

Tests for deterministic semantic type classification and metadata building.
"""

from __future__ import annotations

import pytest

from faim_native.core.operators.semantic_typing import (
    KNOWN_SEMANTIC_KINDS,
    SEMANTIC_WEIGHTS,
    build_semantic_meta,
    classify_semantic_type,
    get_semantic_weight_from_meta,
    should_create_semantic_edge,
)


class TestClassifySemanticType:
    """Test semantic type classification from cosine similarity and node levels."""

    def test_synonym_high_cosine(self):
        """Cosine >= 0.93 should classify as synonym."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.95,
            child_level=0,
            parent_level=0,
        )
        assert semantic_type == "synonym"

    def test_synonym_boundary(self):
        """Cosine exactly at threshold 0.93 should classify as synonym."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.93,
            child_level=0,
            parent_level=0,
        )
        assert semantic_type == "synonym"

    def test_hypernym_parent_higher_level(self):
        """Cosine >= 0.82 with parent_level > child_level should be hypernym."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.85,
            child_level=0,
            parent_level=1,
        )
        assert semantic_type == "hypernym"

    def test_hyponym_parent_lower_level(self):
        """Cosine >= 0.82 with parent_level < child_level should be hyponym."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.85,
            child_level=1,
            parent_level=0,
        )
        assert semantic_type == "hyponym"

    def test_hypernym_tie_break_same_level(self):
        """Cosine >= 0.82 with same level should default to hypernym (tie-break)."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.85,
            child_level=0,
            parent_level=0,
        )
        assert semantic_type == "hypernym"

    def test_hypernym_boundary(self):
        """Cosine exactly at threshold 0.82 should classify correctly."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.82,
            child_level=0,
            parent_level=1,
        )
        assert semantic_type == "hypernym"

    def test_related_moderate_cosine(self):
        """Cosine in range [0.65, 0.82) should classify as related."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.72,
            child_level=0,
            parent_level=0,
        )
        assert semantic_type == "related"

    def test_related_boundary_low(self):
        """Cosine exactly at threshold 0.65 should classify as related."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.65,
            child_level=0,
            parent_level=0,
        )
        assert semantic_type == "related"

    def test_standard_low_cosine(self):
        """Cosine < 0.65 should classify as standard."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.50,
            child_level=0,
            parent_level=0,
        )
        assert semantic_type == "standard"

    def test_standard_boundary(self):
        """Cosine just below 0.65 should classify as standard."""
        semantic_type = classify_semantic_type(
            cosine_sim=0.64,
            child_level=0,
            parent_level=0,
        )
        assert semantic_type == "standard"


class TestBuildSemanticMeta:
    """Test meta dict building for semantic type storage."""

    def test_build_synonym_meta(self):
        """Build meta for synonym type should include correct weight."""
        meta = build_semantic_meta("synonym")
        assert meta["semantic_type"] == "synonym"
        assert meta["semantic_weight"] == SEMANTIC_WEIGHTS["synonym"]
        assert meta["semantic_weight"] == 0.95

    def test_build_hypernym_meta(self):
        """Build meta for hypernym type should include correct weight."""
        meta = build_semantic_meta("hypernym")
        assert meta["semantic_type"] == "hypernym"
        assert meta["semantic_weight"] == SEMANTIC_WEIGHTS["hypernym"]
        assert meta["semantic_weight"] == 0.80

    def test_build_hyponym_meta(self):
        """Build meta for hyponym type should include correct weight."""
        meta = build_semantic_meta("hyponym")
        assert meta["semantic_type"] == "hyponym"
        assert meta["semantic_weight"] == SEMANTIC_WEIGHTS["hyponym"]
        assert meta["semantic_weight"] == 0.75

    def test_build_related_meta(self):
        """Build meta for related type should include correct weight."""
        meta = build_semantic_meta("related")
        assert meta["semantic_type"] == "related"
        assert meta["semantic_weight"] == SEMANTIC_WEIGHTS["related"]
        assert meta["semantic_weight"] == 0.60

    def test_build_standard_meta(self):
        """Build meta for standard type should include 1.0 weight."""
        meta = build_semantic_meta("standard")
        assert meta["semantic_type"] == "standard"
        assert meta["semantic_weight"] == 1.0

    def test_build_unknown_type_defaults_to_standard(self):
        """Unknown semantic type should default to standard."""
        meta = build_semantic_meta("unknown_type")
        assert meta["semantic_type"] == "standard"
        assert meta["semantic_weight"] == 1.0


class TestGetSemanticWeightFromMeta:
    """Test safe extraction of semantic weight from edge meta."""

    def test_extract_weight_from_valid_meta(self):
        """Extract weight from properly formed meta dict."""
        meta = {"semantic_type": "synonym", "semantic_weight": 0.95}
        weight = get_semantic_weight_from_meta(meta)
        assert weight == 0.95

    def test_extract_weight_missing_key(self):
        """Missing semantic_weight key should return default 1.0."""
        meta = {"semantic_type": "synonym"}
        weight = get_semantic_weight_from_meta(meta)
        assert weight == 1.0

    def test_extract_weight_from_none(self):
        """None meta should return default 1.0."""
        weight = get_semantic_weight_from_meta(None)
        assert weight == 1.0

    def test_extract_weight_from_empty_dict(self):
        """Empty meta dict should return default 1.0."""
        weight = get_semantic_weight_from_meta({})
        assert weight == 1.0

    def test_extract_weight_from_non_dict(self):
        """Non-dict meta should return default 1.0."""
        weight = get_semantic_weight_from_meta("not_a_dict")
        assert weight == 1.0


class TestShouldCreateSemanticEdge:
    """Test decision logic for Layer B semantic edge creation."""

    def test_create_edge_for_synonym(self):
        """Synonym type should create semantic edge."""
        should_create = should_create_semantic_edge("synonym")
        assert should_create is True

    def test_create_edge_for_hypernym(self):
        """Hypernym type should create semantic edge."""
        should_create = should_create_semantic_edge("hypernym")
        assert should_create is True

    def test_create_edge_for_hyponym(self):
        """Hyponym type should create semantic edge."""
        should_create = should_create_semantic_edge("hyponym")
        assert should_create is True

    def test_create_edge_for_related(self):
        """Related type should create semantic edge."""
        should_create = should_create_semantic_edge("related")
        assert should_create is True

    def test_create_edge_for_distributional_synonym(self):
        """Distributional synonym type should create semantic edge."""
        should_create = should_create_semantic_edge("distributional_synonym")
        assert should_create is True

    def test_create_edge_for_paraphrase(self):
        """Paraphrase type should create semantic edge."""
        should_create = should_create_semantic_edge("paraphrase")
        assert should_create is True

    def test_no_edge_for_standard(self):
        """Standard type should NOT create semantic edge."""
        should_create = should_create_semantic_edge("standard")
        assert should_create is False

    def test_no_edge_for_unknown(self):
        """Unknown type (defaults to standard) should NOT create semantic edge."""
        should_create = should_create_semantic_edge("unknown_type")
        assert should_create is False


class TestSemanticKinds:
    """Test constants for semantic edge kinds."""

    def test_known_semantic_kinds(self):
        """KNOWN_SEMANTIC_KINDS should include geometry and canonical semantic types."""
        assert "synonym" in KNOWN_SEMANTIC_KINDS
        assert "hypernym" in KNOWN_SEMANTIC_KINDS
        assert "hyponym" in KNOWN_SEMANTIC_KINDS
        assert "related" in KNOWN_SEMANTIC_KINDS
        assert "distributional_synonym" in KNOWN_SEMANTIC_KINDS
        assert "paraphrase" in KNOWN_SEMANTIC_KINDS

    def test_known_semantic_kinds_count(self):
        """KNOWN_SEMANTIC_KINDS should include multilingual semantic types too."""
        assert "concept_surface" in KNOWN_SEMANTIC_KINDS
        assert "translation" in KNOWN_SEMANTIC_KINDS
        assert "entity_alias" in KNOWN_SEMANTIC_KINDS
        assert "entity_relation" in KNOWN_SEMANTIC_KINDS
        assert "fact_value" in KNOWN_SEMANTIC_KINDS
        assert len(KNOWN_SEMANTIC_KINDS) == 15

    def test_semantic_weights_completeness(self):
        """SEMANTIC_WEIGHTS should include all semantic types and standard."""
        assert "synonym" in SEMANTIC_WEIGHTS
        assert "hypernym" in SEMANTIC_WEIGHTS
        assert "hyponym" in SEMANTIC_WEIGHTS
        assert "related" in SEMANTIC_WEIGHTS
        assert "distributional_synonym" in SEMANTIC_WEIGHTS
        assert "paraphrase" in SEMANTIC_WEIGHTS
        assert "standard" in SEMANTIC_WEIGHTS
