from __future__ import annotations

from faim_native.encoding.semantic_signature import build_semantic_signature


def test_semantic_signature_is_deterministic():
    text = "AI revenue improved 15% before 2026 in München."
    first = build_semantic_signature(text)
    second = build_semantic_signature(text)

    assert first == second


def test_semantic_signature_extracts_concepts_aliases_and_transliteration():
    signature = build_semantic_signature(
        "AI revenue improved 15% before 2026 in München after acquisition."
    )

    assert signature.semantic_phrase_counts
    assert signature.concept_counts
    assert signature.morphology_counts
    assert any(item.startswith("alias:ai|") for item in signature.alias_families)
    assert "muenchen" in signature.transliterated_tokens
    assert "relation:acquire" in signature.relation_cues
    assert "value:percent" in signature.value_cues
    assert "time:before" in signature.temporal_cues


def test_semantic_signature_extracts_multilingual_and_morphology_channels():
    signature = build_semantic_signature(
        "Multilingual translation systems were running efficiently for legal operations."
    )

    assert signature.concept_counts
    assert signature.morphology_counts
    assert "relation:run" in signature.relation_cues
    assert any(item.startswith("stem:translat") for item in signature.stem_families)
    assert not any(item.startswith("alias:") for item in signature.alias_families)
