from __future__ import annotations

from unittest.mock import patch

from faim_native.lexical.canonicalizer import canonicalize_text
from faim_native.lexical.multilingual_canonicalizer import (
    canonicalize_multilingual_text,
)
from faim_native.lexical.synonym_expander import (
    WeightedExpansion,
    build_weighted_synonym_expansions,
    merge_weighted_expansions,
    render_weighted_expansion_text,
)


def test_merge_weighted_expansions_dedupes_and_preserves_sources():
    merged = merge_weighted_expansions(
        [
            WeightedExpansion("revenue", 0.7, ("conceptnet_token",), ("sales",)),
            WeightedExpansion("revenue", 0.91, ("canonical_lemma",), ("sale",)),
            WeightedExpansion("margin", 0.6, ("conceptnet_token",), ("profit",)),
        ]
    )

    assert [item.term for item in merged] == ["revenue", "margin"]
    assert merged[0].weight == 0.91
    assert merged[0].sources == ("canonical_lemma", "conceptnet_token")
    assert "sale" in merged[0].origins
    assert "sales" in merged[0].origins


def test_build_weighted_synonym_expansions_is_capped_and_deterministic():
    fake = {
        "revenue": ["sales", "income", "turnover"],
        "quarter": ["trimester", "period"],
        "revenue quarter": ["financial quarter"],
    }
    with patch("faim_native.lexical.synonym_expander._synonyms", fake), patch(
        "faim_native.lexical.synonym_expander._AVAILABLE", True
    ):
        first = build_weighted_synonym_expansions(
            "revenue quarter", max_synonyms_per_term=2, max_total=3
        )
        second = build_weighted_synonym_expansions(
            "revenue quarter", max_synonyms_per_term=2, max_total=3
        )

    assert first == second
    assert len(first) == 3
    assert first[0].sources[0].startswith("conceptnet_phrase")


def test_render_weighted_expansion_text_respects_weight_bands():
    rendered = render_weighted_expansion_text(
        "revenue quarter",
        [
            WeightedExpansion("sales", 0.97, ("canonical_phrase",)),
            WeightedExpansion("income", 0.83, ("conceptnet_token",)),
            WeightedExpansion("period", 0.61, ("conceptnet_token",)),
        ],
        max_total_terms=8,
    )
    assert rendered.count("sales") == 3
    assert rendered.count("income") == 2
    assert rendered.count("period") == 1


def test_canonicalize_text_emits_weighted_phrase_and_lemma_expansions():
    item = canonicalize_text(
        "RCP latency",
        canonical_map={
            "rcp": ("retrieval control plane",),
            "rcp latency": ("retrieval_latency",),
        },
    )
    assert "retrieval control plane" in item.expansions
    assert any(exp.term == "retrieval control plane" for exp in item.weighted_expansions)
    assert any("canonical_lemma" in exp.sources for exp in item.weighted_expansions)


def test_multilingual_canonicalizer_emits_weighted_translation_and_graph_rows():
    item = canonicalize_multilingual_text(
        "umsatz quartal",
        graph_map={"umsatz": ("income_statement",)},
    )
    assert any(exp.term.startswith("concept:") for exp in item.weighted_expansions)
    assert any("multilingual_translation" in exp.sources for exp in item.weighted_expansions)
    assert any("graph_multilingual" in exp.sources for exp in item.weighted_expansions)
    assert any("multilingual_bridge" in exp.sources for exp in item.weighted_expansions)
