"""Regression tests for additive retrieval telemetry in the query contract."""

from faim_native.api.routers.query import QueryMetrics


def test_query_metrics_accepts_stage_timings_without_changing_existing_defaults():
    metrics = QueryMetrics(
        node_count=5,
        stage_timings_ms={"candidate_recall_ms": 1.25, "rerank_ms": 2.5},
    )

    assert metrics.node_count == 5
    assert metrics.stage_timings_ms["rerank_ms"] == 2.5


def test_query_metrics_defaults_stage_timings_to_empty_mapping():
    assert QueryMetrics().stage_timings_ms == {}
