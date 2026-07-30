"""Unit tests for Phase 4 proposition extraction."""

from __future__ import annotations

from faim_native.core.query.proposition_extractor import (
    extract_propositions,
    proposition_overlap,
    proposition_signature,
)
from faim_native.encoding.representation_v2 import build_representation_v2


def test_extract_propositions_finds_relation_entity_and_time():
    text = "Atlas lives in Berlin in 2026 and invoice INV-2026 reached 15%."
    repr_v2 = build_representation_v2(text)
    analysis = extract_propositions(text, representation=repr_v2)

    assert "rel:located_in" in analysis.relations
    assert "inv-2026" in analysis.entities
    assert "year:2026" in analysis.times
    assert any(prop.relation == "rel:located_in" for prop in analysis.propositions)


def test_proposition_overlap_and_signature_are_deterministic():
    left = extract_propositions("Atlas lives in Berlin in 2026.")
    right = extract_propositions("Atlas resides in Berlin in 2026.")

    overlap_one = proposition_overlap(left, right)
    overlap_two = proposition_overlap(left, right)

    assert overlap_one == overlap_two
    assert overlap_one > 0.6
    assert proposition_signature(left) == proposition_signature(left)
