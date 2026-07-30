"""Unit tests for deterministic rule-based lemmatization."""

from __future__ import annotations

from faim_native.lexical.lemmatizer_rules import lemmatize_token, lemmatize_tokens


def test_lemmatize_plural_and_progressive_forms():
    assert lemmatize_token("systems") == "system"
    assert lemmatize_token("running") == "run"
    assert lemmatize_token("cities") == "city"
    assert lemmatize_token("lives") == "live"


def test_lemmatize_tokens_keeps_order_and_filters_empty():
    assert lemmatize_tokens(["", "works", "in", "berlin"]) == ["work", "in", "berlin"]
