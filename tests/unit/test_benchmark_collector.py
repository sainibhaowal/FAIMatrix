from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from api.services.benchmark_collector import BenchmarkCollector, BenchmarkSuiteRun, BenchmarkItem


class DummyEventRepo:
    def __init__(self, events):
        self._events = events

    def get_by_seq(self, session, graph_id, after_seq=0, limit=100):
        return list(self._events)


def test_series_points_from_benchmark_event():
    run_payload = {
        "run": {
            "computed_at": "2026-04-19T00:00:00+00:00",
            "node_count": 12,
            "compression_ratio": 0.75,
            "benchmarks": [
                {"benchmark_id": "BM-1", "score": 100.0},
                {"benchmark_id": "BM-2", "score": 100.0},
                {"benchmark_id": "BM-3", "score": 100.0},
                {"benchmark_id": "BM-4", "score": 100.0},
                {"benchmark_id": "BM-5", "score": 80.0},
            ],
            "summary": {"max_lambda_hat": 0.42, "latest_ingest_latency_ms": 18},
            "throughput_synapses_per_sec": 9.5,
        }
    }
    event = SimpleNamespace(kind="BENCHMARK_SUITE_RESULT", payload=run_payload, ts=datetime.now(timezone.utc))
    ctx = SimpleNamespace(session=SimpleNamespace(), event_repo=DummyEventRepo([event]))
    collector = BenchmarkCollector(ctx)

    points = collector.series_points("U:test", limit=10)

    assert len(points) == 1
    assert points[0]["nodes"] == 12
    assert points[0]["cr"] == 0.75
    assert points[0]["latency"]["store_p50_ms"] == 18

    runs = collector.list_runs("U:test", limit=10)
    assert len(runs) == 1
    assert runs[0]["node_count"] == 12

    found = collector.get_run("U:test", run_id=runs[0].get("run_id", ""))
    if runs[0].get("run_id"):
        assert found is not None


def test_benchmark_suite_and_persistence_shape(monkeypatch):
    from api.services import benchmark_collector as collector_module

    nodes = [
        SimpleNamespace(node_id="n1", vector_hash="a" * 64, level=0, residual=0, touch_count=1, v_native=[0.1] * 256),
        SimpleNamespace(node_id="n2", vector_hash="b" * 64, level=1, residual=100000000, touch_count=3, v_native=[0.2] * 256),
    ]
    edges = [SimpleNamespace(edge_id="e1", src_node_id="n1", dst_node_id="n2", kind="inheritance", weight=1000000000)]
    diagnostics = SimpleNamespace(
        node_count=2,
        edge_count=1,
        lambda_hat=0.64,
        diagnostics_hash="c" * 64,
    )
    fake_state = collector_module.GraphState(
        tenant_id="tenant-a",
        graph_id="U:test",
        graph_version=7,
        nodes=nodes,
        edges=edges,
        vectors=[[0.1] * 256, [0.2] * 256],
        residuals=[0.0, 0.1],
        graph_hash="d" * 64,
        diagnostics=diagnostics,
        diagnostics_hash=diagnostics.diagnostics_hash,
        diagnostics_event=SimpleNamespace(kind="DIAGNOSTICS_SNAPSHOT", payload={"graph_hash": "d" * 64}),
        ingest_latency_event=SimpleNamespace(kind="INGEST_PHASE_LATENCY", payload={"latency_ms": 18, "phase_latency_ms": {"extract": 4, "encode": 6}}),
        latest_evolution_event=SimpleNamespace(kind="EVOLUTION_COMPLETE", payload={"merges": 1, "prunes": 1, "inventions": 1}),
        events=[],
    )

    class DummyRepo:
        def list_nodes(self, graph_id, limit=10000):
            return nodes

        def list_all_edges(self, graph_id, limit=20000):
            return edges

        def count(self, graph_id):
            return len(nodes)

        def get_by_seq(self, session, graph_id, after_seq=0, limit=100):
            return []

    class DummyGVRepo:
        def get_or_create(self, session, graph_id):
            return SimpleNamespace(version=7)

    emitted = []

    class DummyEventRepo:
        def emit(self, session, graph_id, kind, payload):
            emitted.append((graph_id, kind, payload))
            return SimpleNamespace(id="event-1", kind=kind, payload=payload, ts=datetime.now(timezone.utc))

        def get_by_seq(self, session, graph_id, after_seq=0, limit=100):
            return []

    ctx = SimpleNamespace(
        tenant_id="tenant-a",
        session=SimpleNamespace(commit=lambda: None, rollback=lambda: None),
        node_repo=DummyRepo(),
        edge_repo=DummyRepo(),
        event_repo=DummyEventRepo(),
        gv_repo=DummyGVRepo(),
        cache=None,
    )
    collector = BenchmarkCollector(ctx)

    monkeypatch.setattr(BenchmarkCollector, "_build_graph_state", lambda self, graph_id: fake_state)
    monkeypatch.setattr(
        BenchmarkCollector,
        "_query_without_persist",
        lambda self, graph_id, query_text, k=5: {
            "tenant_id": "tenant-a",
            "graph_id": graph_id,
            "graph_version": 7,
            "graph_hash": fake_state.graph_hash,
            "query_hash": "q" * 64,
            "k": 5,
            "results": [{"node_id": "n1", "score": 0.9, "explain": {"reason": "stable"}}],
            "metrics": {"node_count": 2},
            "duration_ms": 10.0,
        },
    )
    monkeypatch.setattr(collector_module, "check_all_invariants", lambda node_repo, edge_repo, graph_id: SimpleNamespace(passed=True, checks=[{"passed": True}], errors=[]))
    monkeypatch.setattr(collector_module.global_throughput, "get_throughput", lambda: 11.5)

    run = collector.run_suite("U:test")
    assert len(run.benchmarks) == 9
    assert run.benchmarks[0].benchmark_id == "BM-1"
    assert run.benchmarks[-1].benchmark_id == "BM-9"

    collector.persist_suite("U:test", run)
    benchmark_events = [event for event in emitted if event[1] == "BENCHMARK_SUITE_RESULT"]
    assert benchmark_events
    assert benchmark_events[-1][2]["run"]["graph_id"] == "U:test"


def test_benchmark_suite_to_dict_includes_scores():
    item = BenchmarkItem(
        benchmark_id="BM-1",
        name="Determinism Proof",
        passed=True,
        score=100.0,
        evidence_hash="e" * 64,
        evidence={"ok": True},
        notes=["stable"],
    )
    run = BenchmarkSuiteRun(
        run_id="run-1",
        tenant_id="tenant-a",
        graph_id="U:test",
        graph_version=1,
        graph_hash="f" * 64,
        diagnostics_hash="g" * 64,
        computed_at="2026-04-19T00:00:00+00:00",
        duration_ms=12,
        node_count=1,
        edge_count=0,
        atom_count=1,
        macro_count=0,
        compression_ratio=1.0,
        throughput_synapses_per_sec=3.2,
        budget_profile="STRICT",
        benchmarks=[item],
        summary={"overall_score": 100.0},
    )

    data = run.to_dict()

    assert data["overall_score"] == 100.0
    assert data["benchmark_count"] == 1
    assert data["benchmarks"][0]["benchmark_id"] == "BM-1"


def test_get_run_returns_none_for_unknown_id():
    event = SimpleNamespace(kind="BENCHMARK_SUITE_RESULT", payload={"run": {"run_id": "known-id"}}, ts=datetime.now(timezone.utc))
    ctx = SimpleNamespace(session=SimpleNamespace(), event_repo=DummyEventRepo([event]))
    collector = BenchmarkCollector(ctx)

    assert collector.get_run("U:test", "missing-id") is None
