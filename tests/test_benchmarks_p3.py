# ============================================================================
#  P3 BENCHMARK RECORD CONTRACT TESTS – FAIM SCRIPTS
# ----------------------------------------------------------------------------
#  What we verify here
#  -------------------
#  - scripts.benchmarks.build_benchmark_record(...) exists.
#  - It returns a JSON-serialisable dict with:
#       * top-level keys: graph_id, timestamp, nodes, workload, engine, metrics
#       * metrics: cr, redundancy, drift, latency
#       * latency: p50_ms, p95_ms, max_ms, count
#
#  This is a schema / wiring test only. It does not validate *real* numbers.
# ============================================================================

from typing import Any, Dict, cast

import scripts.benchmarks as benchmarks
from faim.core import metrics
from faim.core.types import GraphId

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _make_fake_metrics() -> Dict[str, Any]:
    lat = metrics.LatencyStats(
        graph_id=cast(GraphId, "TEST_GRAPH"),
        p50_ms=1.0,
        p95_ms=2.0,
        max_ms=3.0,
        count=10,
    )
    return {
        "cr": 10.0,
        "redundancy": 0.1,
        "drift": 0.02,
        "latency": lat,
    }


def _make_fake_workload() -> benchmarks.WorkloadSpec:
    return benchmarks.WorkloadSpec(
        name="unit_test",
        description="Unit-test synthetic workload",
        kind="synthetic",
    )


def _make_fake_engine_info() -> benchmarks.EngineInfo:
    return benchmarks.EngineInfo(
        engine_name="FAIMEngine",
        profile="Default",
        persist_mode="relaxed",
    )


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------


def test_benchmark_record_schema() -> None:
    """
    P3 contract: build_benchmark_record must produce a JSON-serialisable
    dict with the expected schema so FAIM Lab UI can consume it directly.
    """
    record = benchmarks.build_benchmark_record(
        graph_id="TEST_GRAPH",
        nodes=123,
        metrics=_make_fake_metrics(),
        workload=_make_fake_workload(),
        engine_info=_make_fake_engine_info(),
    )

    # Top-level shape ------------------------------------------------------
    assert isinstance(record, dict)
    assert record["graph_id"] == "TEST_GRAPH"
    assert record["nodes"] == 123
    assert "timestamp" in record

    workload = record["workload"]
    engine = record["engine"]
    metrics_block = record["metrics"]

    assert workload["name"] == "unit_test"
    assert workload["kind"] == "synthetic"
    assert "description" in workload

    assert engine["engine_name"] == "FAIMEngine"
    assert engine["profile"] == "Default"
    assert engine["persist_mode"] == "relaxed"

    # Metrics block --------------------------------------------------------
    assert "cr" in metrics_block
    assert "redundancy" in metrics_block
    assert "drift" in metrics_block
    assert "latency" in metrics_block

    assert isinstance(metrics_block["cr"], float)
    assert isinstance(metrics_block["redundancy"], float)
    assert isinstance(metrics_block["drift"], float)

    # Latency block must be a dict with the standard keys.
    latency = metrics_block["latency"]
    assert isinstance(latency, dict)
    for key in ("p50_ms", "p95_ms", "max_ms", "count"):
        assert key in latency

    # Basic sanity ranges (not strict, just non-negative / positive).
    assert latency["p50_ms"] >= 0.0
    assert latency["p95_ms"] >= 0.0
    assert latency["max_ms"] >= 0.0
    assert latency["count"] > 0
