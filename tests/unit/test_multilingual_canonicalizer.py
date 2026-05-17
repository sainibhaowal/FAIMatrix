from __future__ import annotations

from faim_native.lexical.multilingual_canonicalizer import (
    canonicalize_multilingual_text,
    detect_language,
)


def test_detect_language_en_and_de():
    assert detect_language("revenue quarter city") == "en"
    assert detect_language("umsatz quartal stadt") == "de"


def test_multilingual_canonicalizer_adds_concept_and_translation():
    item = canonicalize_multilingual_text("umsatz quartal")
    assert item.language == "de"
    assert any(value.startswith("concept:") for value in item.expansions)
    assert "revenue" in item.expansions or "quarter" in item.expansions
