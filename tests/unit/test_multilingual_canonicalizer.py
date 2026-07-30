from __future__ import annotations

from faim_native.lexical.multilingual_canonicalizer import (
    canonicalize_multilingual_text,
    detect_language,
    load_multilingual_resources,
)


def test_detect_language_en_and_de():
    assert detect_language("revenue quarter city") == "en"
    assert detect_language("umsatz quartal stadt") == "de"


def test_detect_language_spanish_and_french():
    assert detect_language("ingresos trimestre ciudad") == "es"
    assert detect_language("revenus trimestre ville") == "fr"


def test_multilingual_canonicalizer_adds_concept_and_translation():
    item = canonicalize_multilingual_text("umsatz quartal")
    assert item.language == "de"
    assert any(value.startswith("concept:") for value in item.expansions)
    assert "revenue" in item.expansions or "quarter" in item.expansions


def test_multilingual_canonicalizer_emits_cross_language_bridge_terms():
    item = canonicalize_multilingual_text("ingresos trimestre")
    assert item.language == "es"
    assert any("multilingual_translation" in exp.sources for exp in item.weighted_expansions)
    assert any("multilingual_bridge" in exp.sources for exp in item.weighted_expansions)


def test_multilingual_resources_cover_enterprise_languages_and_are_deterministic():
    _by_language, _surfaces, supported_languages = load_multilingual_resources()

    assert supported_languages == tuple(sorted({"en", "de", "es", "fr", "it", "pt", "nl"}))

    first = canonicalize_multilingual_text("revenus trimestre")
    second = canonicalize_multilingual_text("revenus trimestre")

    assert first == second
    assert first.language == "fr"
    assert any(exp.term.startswith("concept:") for exp in first.weighted_expansions)
