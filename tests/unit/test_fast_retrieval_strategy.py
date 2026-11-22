"""Tests for the production-safe FAST retrieval strategy gates."""

from faim_native.api.routers.query import QueryMetrics
from faim_native.core.query.query_engine import (
    FUSION_LAYER_WEIGHTS,
    RELEVANCE_FIRST_FUSION_LAYER_WEIGHTS,
)
from faim_native.orchestration.ingest_flow import FAIMProfile
from faim_native.orchestration.query_flow import (
    _fast_graph_expansion_enabled,
    _fast_idf_enabled,
    _fast_relevance_first_enabled,
)


def test_fast_defaults_to_relevance_first(monkeypatch):
    monkeypatch.delenv("FAIM_FAST_RELEVANCE_FIRST", raising=False)
    monkeypatch.setenv("FAIM_REPR_V2_ENABLED", "true")

    assert _fast_relevance_first_enabled(FAIMProfile.FAST) is True
    assert _fast_relevance_first_enabled(FAIMProfile.STRICT) is False


def test_fast_graph_and_idf_are_bounded_by_default(monkeypatch):
    monkeypatch.delenv("FAIM_FAST_GRAPH_EXPANSION", raising=False)
    monkeypatch.delenv("FAIM_FAST_IDF", raising=False)

    assert _fast_graph_expansion_enabled(FAIMProfile.FAST) is False
    assert _fast_idf_enabled(FAIMProfile.FAST) is False
    assert _fast_graph_expansion_enabled(FAIMProfile.BALANCED) is True
    assert _fast_idf_enabled(FAIMProfile.BALANCED) is True


def test_fast_flags_support_explicit_rollback(monkeypatch):
    monkeypatch.setenv("FAIM_FAST_GRAPH_EXPANSION", "true")
    monkeypatch.setenv("FAIM_FAST_IDF", "true")
    monkeypatch.setenv("FAIM_FAST_RELEVANCE_FIRST", "false")

    assert _fast_graph_expansion_enabled(FAIMProfile.FAST) is True
    assert _fast_idf_enabled(FAIMProfile.FAST) is True
    assert _fast_relevance_first_enabled(FAIMProfile.FAST) is False


def test_relevance_first_fusion_prioritizes_lexical_evidence():
    assert (
        RELEVANCE_FIRST_FUSION_LAYER_WEIGHTS["lexical_fusion"]
        > FUSION_LAYER_WEIGHTS["lexical_fusion"]
    )
    assert (
        RELEVANCE_FIRST_FUSION_LAYER_WEIGHTS["graph_semantics"]
        < FUSION_LAYER_WEIGHTS["graph_semantics"]
    )


def test_fast_diagnostics_are_additive_api_fields():
    metrics = QueryMetrics(
        fast_relevance_first=1.0,
        fast_graph_expansion=0.0,
        fast_idf=0.0,
    )
    assert metrics.fast_relevance_first == 1.0
    assert metrics.fast_graph_expansion == 0.0
    assert metrics.fast_idf == 0.0
