from __future__ import annotations

from unittest.mock import patch

from faim_native.lexical.semantic_registry import (
    load_semantic_registry_snapshot,
    resolve_semantic_registry_expansions,
)


def test_semantic_registry_snapshot_reports_real_loaded_sources():
    with patch("faim_native.lexical.semantic_registry.synonym_expander._synonyms", {"revenue": ["sales"]}), patch(
        "faim_native.lexical.semantic_registry.is_available", return_value=True
    ):
        load_semantic_registry_snapshot.cache_clear()
        snapshot = load_semantic_registry_snapshot()

    assert snapshot.conceptnet_terms == 1
    assert snapshot.static_lexicon_terms > 0
    assert snapshot.total_terms >= snapshot.static_lexicon_terms
    assert "en" in snapshot.supported_languages


def test_semantic_registry_resolves_expansions_from_all_layers():
    with patch(
        "faim_native.lexical.semantic_registry.get_weighted_synonyms",
        return_value=(),
    ), patch(
        "faim_native.lexical.semantic_registry.is_available",
        return_value=False,
    ):
        expansions, info = resolve_semantic_registry_expansions(
            query_text="rcp umsatz heartbeat",
            canonical_map={"rcp": ("retrieval control plane",)},
            multilingual_map={"umsatz": ("revenue", "quarterly revenue")},
            domain_map={"heartbeat": ("heart rate",)},
            max_total=10,
        )

    terms = [item.term for item in expansions]
    assert "retrieval control plane" in terms
    assert "revenue" in terms
    assert "heart rate" in terms
    assert "rcp" in info["matched_surfaces"]["canonical"]
    assert "umsatz" in info["matched_surfaces"]["multilingual"]
    assert "heartbeat" in info["matched_surfaces"]["domain"]
