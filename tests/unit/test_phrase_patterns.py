"""Unit tests for deterministic phrase rewrite templates."""

from __future__ import annotations

from faim_native.lexical.phrase_patterns import (
    extract_phrase_labels,
    extract_phrase_surface_map,
)


def test_extract_phrase_labels_matches_surface_variants():
    tokens = ["atlas", "resides", "in", "berlin", "and", "works", "for", "helios"]
    labels = extract_phrase_labels(tokens)
    mapping = extract_phrase_surface_map(tokens)

    assert "rel:located_in" in labels
    assert "rel:employed_by" in labels
    assert mapping["resides in"] == "rel:located_in"
    assert mapping["works for"] == "rel:employed_by"
