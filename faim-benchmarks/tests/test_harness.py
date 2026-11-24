"""End-to-end verification tests for faim-benchmarks."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
from faim_benchmarks.adapters import (
    BM25BaselineAdapter,
    FaimHttpAdapter,
)
from faim_benchmarks.adapters.base import IngestOutcome
from faim_benchmarks.datasets import (
    load_beir_split,
    load_locomo_split,
    load_longmemeval_split,
)
from faim_benchmarks.metrics import (
    bootstrap_ci,
    compute_ir_metrics,
    exact_match,
    token_f1,
)
from faim_benchmarks.report import (
    compute_payload_sha256,
    evaluate_publication_gate,
    write_signed_artifacts,
)
from faim_benchmarks.runner import run_conversational_benchmark, run_retrieval_benchmark


def test_metrics_and_bootstrap_deterministic():
    ir = compute_ir_metrics(["d1", "d2", "d3"], {"d1": 1.0, "d3": 1.0}, k_values=(1, 5))
    assert ir["recall@1"] == 0.5
    assert ir["recall@5"] == 1.0
    assert 0.8 < ir["ndcg@5"] <= 1.0
    assert ir["mrr"] == 1.0

    ci_a = bootstrap_ci([1.0, 0.5, 1.0, 0.0], iterations=200, seed=42)
    ci_b = bootstrap_ci([1.0, 0.5, 1.0, 0.0], iterations=200, seed=42)
    assert ci_a == ci_b
    assert ci_a["ci_low"] <= ci_a["mean"] <= ci_a["ci_high"]
    assert exact_match("The Paris!", "paris") == 1.0
    assert token_f1("Paris France", "Paris") > 0.6


def test_local_beir_runner_and_signed_reports(tmp_path: Path):
    beir_dir = tmp_path / "beir"
    (beir_dir / "qrels").mkdir(parents=True)
    (beir_dir / "corpus.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "_id": "d1",
                        "title": "FAIM",
                        "text": "Fractal antisymmetric inheritance memory uses multi-hop graph retrieval.",
                    }
                ),
                json.dumps(
                    {
                        "_id": "d2",
                        "title": "Cooking",
                        "text": "Boil water and add pasta for ten minutes.",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    (beir_dir / "queries.jsonl").write_text(
        json.dumps({"_id": "q1", "text": "fractal antisymmetric graph retrieval"}),
        encoding="utf-8",
    )
    (beir_dir / "qrels" / "test.tsv").write_text(
        "query-id\tcorpus-id\tscore\nq1\td1\t1\n", encoding="utf-8"
    )

    split = load_beir_split("mini", local_dir=str(beir_dir))

    def faim_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/ingest":
            return httpx.Response(
                200,
                json={"status": "completed", "packet_hash": "abc", "graph_version": 1},
            )
        if request.url.path == "/api/v1/query":
            body = json.loads(request.content.decode("utf-8"))
            raw_d1 = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"faim-bench:{body['graph_id']}:d1")
            )
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"node_id": "n1", "score": 0.99, "evidence": {"raw_id": raw_d1}}
                    ],
                    "answer": {
                        "direct_answer": "Fractal antisymmetric inheritance memory",
                        "supporting_spans": [],
                    },
                    "metrics": {
                        "phase5_sparse_candidates": 20,
                        "phase5_dense_candidates": 20,
                        "stage_timings_ms": {
                            "candidate_recall_ms": 1.25,
                            "rerank_ms": 2.5,
                        },
                    },
                    "degraded_features": [],
                },
            )
        return httpx.Response(404)

    faim = FaimHttpAdapter(
        base_url="http://faim.test",
        api_key="k",
        tenant_id="t",
        transport=httpx.MockTransport(faim_handler),
    )
    class UnconfiguredAdapter:
        name = "Unconfigured-Baseline"
        system_type = "test"

        def is_configured(self):
            return False, "UNCONFIGURED_API_KEY not set"

        def prepare_namespace(self, namespace):
            return None

        def ingest_document(self, namespace, doc_id, title, text):
            return IngestOutcome(doc_id=doc_id, latency_ms=0.0)

        def write_memory(self, namespace, memory_id, text, timestamp=None):
            return IngestOutcome(doc_id=memory_id, latency_ms=0.0)

        def query(self, namespace, query_id, query_text, k=20):
            raise NotImplementedError

        def close(self):
            return None

    unconfigured_adapter = UnconfiguredAdapter()
    bm25 = BM25BaselineAdapter()

    result = run_retrieval_benchmark(
        split=split,
        adapters=[faim, bm25, unconfigured_adapter],
        top_k=5,
        seed=42,
        bootstrap_iterations=50,
        retain_query_traces=True,
    )
    json_path, md_path = write_signed_artifacts(result, tmp_path / "results")
    saved = json.loads(json_path.read_text(encoding="utf-8"))

    assert saved["integrity_sha256"] == compute_payload_sha256(saved)
    assert saved["publication_gate"]["ready"] is False
    assert "unconfigured systems: Unconfigured-Baseline" in saved["publication_gate"]["reasons"]
    assert md_path.exists()
    by_sys = {s["system"]: s for s in saved["systems"]}
    assert by_sys["FAIM-Native"]["status"] == "completed"
    assert by_sys["FAIM-Native"]["metrics"]["recall@5"] == 1.0
    assert by_sys["FAIM-Native"]["query_trace_count"] == 1
    assert by_sys["FAIM-Native"]["query_traces"][0]["retrieved_doc_ids"] == ["d1"]
    assert "query_text" not in by_sys["FAIM-Native"]["query_traces"][0]
    assert (
        by_sys["FAIM-Native"]["query_traces"][0]["metadata"]["response_metrics"][
            "stage_timings_ms"
        ]["rerank_ms"]
        == 2.5
    )
    assert by_sys["BM25-Baseline"]["metrics"]["recall@5"] == 1.0
    assert by_sys["Unconfigured-Baseline"]["status"] == "skipped"


def test_faim_batch_query_does_not_scan_complete_storage_catalog(monkeypatch):
    monkeypatch.setenv("FAIM_BENCHMARK_MODE", "true")

    def fail_catalog_scan(request: httpx.Request) -> httpx.Response:
        raise AssertionError("batch mappings should avoid a catalog scan")

    adapter = FaimHttpAdapter(
        base_url="http://faim.test",
        api_key="k",
        tenant_id="t",
        transport=httpx.MockTransport(fail_catalog_scan),
    )
    namespace = "benchmark-graph"
    adapter.prepare_namespace(namespace)
    adapter._filename_to_doc[namespace] = {"bench_d1.txt": "d1"}
    adapter._raw_to_doc[namespace] = {"raw-d1": "d1"}

    adapter._sync_storage_raw_ids(namespace)

    assert namespace in adapter._synced_namespaces


def test_conversational_locomo_and_longmemeval_loaders_and_adapters(tmp_path: Path):
    locomo_file = tmp_path / "locomo.json"
    locomo_file.write_text(
        json.dumps(
            [
                {
                    "conversation": {
                        "session_1_date_time": "2026-01-01",
                        "session_1": [
                            {
                                "speaker": "Alice",
                                "text": "My project codename is Hyperion.",
                            }
                        ],
                    },
                    "qa": [
                        {
                            "category": "single-hop",
                            "question": "What is Alice's project codename?",
                            "answer": "Hyperion",
                            "evidence": ["D1:1"],
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    lme_file = tmp_path / "lme.json"
    lme_file.write_text(
        json.dumps(
            [
                {
                    "question_id": "q_lme_1",
                    "question_type": "temporal",
                    "haystack_dates": ["2026-02-01"],
                    "haystack_sessions": [
                        [
                            {
                                "role": "user",
                                "content": "Switched database from SQLite to Postgres.",
                            }
                        ]
                    ],
                    "question": "Which database did the user switch to?",
                    "answer": "Postgres",
                    "answer_session_ids": ["0"],
                }
            ]
        ),
        encoding="utf-8",
    )

    locomo_split = load_locomo_split(str(locomo_file))
    lme_split = load_longmemeval_split(str(lme_file))
    assert len(locomo_split.qa_cases) == 1
    assert len(lme_split.qa_cases) == 1

    bm25 = BM25BaselineAdapter()
    res = run_conversational_benchmark(
        split=locomo_split,
        adapters=[bm25],
        top_k=5,
        seed=42,
        bootstrap_iterations=20,
    )
    by_sys = {s["system"]: s for s in res["systems"]}
    assert by_sys["BM25-Baseline"]["metrics"]["fact_recall"] == 1.0
    assert "single-hop" in by_sys["BM25-Baseline"]["category_breakdown"]
    assert "query_iqr_ms" in by_sys["BM25-Baseline"]["latency_ms"]
    assert by_sys["BM25-Baseline"]["context_tokens"]["avg"] > 0


def test_failed_adapter_is_reported_without_aborting_other_systems():
    class BrokenAdapter:
        name = "Broken-System"
        system_type = "test"

        def is_configured(self):
            return True, None

        def prepare_namespace(self, namespace):
            return None

        def ingest_document(self, namespace, doc_id, title, text):
            return IngestOutcome(doc_id=doc_id, latency_ms=0.1)

        def write_memory(self, namespace, memory_id, text, timestamp=None):
            return IngestOutcome(doc_id=memory_id, latency_ms=0.1)

        def query(self, namespace, query_id, query_text, k=20):
            raise RuntimeError("simulated upstream outage")

        def close(self):
            return None

    split = type(
        "Split",
        (),
        {
            "name": "failure-isolation",
            "corpus": {"d1": {"title": "Title", "text": "content"}},
            "queries": {"q1": "content"},
            "qrels": {"q1": {"d1": 1.0}},
        },
    )()
    result = run_retrieval_benchmark(
        split=split,
        adapters=[BrokenAdapter(), BM25BaselineAdapter()],
        bootstrap_iterations=10,
    )
    rows = {row["system"]: row for row in result["systems"]}
    assert rows["Broken-System"]["status"] == "failed"
    assert "simulated upstream outage" in rows["Broken-System"]["reason"]
    assert rows["Broken-System"]["metrics"] == {}
    assert rows["BM25-Baseline"]["status"] == "completed"


def test_retrieval_quality_gates_block_underperforming_faim():
    gate = evaluate_publication_gate(
        {
            "suite_type": "retrieval_beir",
            "systems": [
                {
                    "system": "FAIM-Native",
                    "status": "completed",
                    "metrics": {"ndcg@10": 0.40},
                    "latency_ms": {"query_p95": 900.0},
                },
                {
                    "system": "BM25-Baseline",
                    "status": "completed",
                    "metrics": {"ndcg@10": 0.60},
                    "latency_ms": {"query_p95": 10.0},
                },
            ],
            "dataset_metadata": {"sampling": {}, "source_type": "local_beir_folder"},
            "run_metadata": {
                "git_commit": "abc123",
                "git_worktree_dirty": False,
                "query_traces_retained": True,
                "model_provenance": {
                    "embedding_provider_id": "local",
                    "embedding_model_id": "model",
                    "embedding_model_revision": "rev",
                },
                "quality_gates": {
                    "min_ndcg_at_10": 0.50,
                    "max_query_p95_ms": 500.0,
                    "require_faim_beats_bm25": True,
                },
            },
        }
    )

    assert gate["ready"] is False
    assert any("below gate" in reason for reason in gate["reasons"])
    assert any("exceeds gate" in reason for reason in gate["reasons"])
    assert any("does not exceed BM25" in reason for reason in gate["reasons"])


def test_conversational_parallel_sessions_preserve_order():
    import threading
    from faim_benchmarks.adapters.base import QueryOutcome
    from faim_benchmarks.datasets import (
        ConversationalBenchmarkSplit,
        ConversationalTurn,
        MemoryQACase,
    )

    turns = [
        ConversationalTurn(
            speaker="user",
            text=f"s{s}_m{m}",
            timestamp=f"2026-01-01T00:0{s}:0{m}Z",
            session_id=f"s{s}",
        )
        for s in range(4)
        for m in range(3)
    ]
    split = ConversationalBenchmarkSplit(
        name="parallel_mem",
        turns=turns,
        qa_cases=[
            MemoryQACase(
                case_id=f"q{i}",
                category="temporal",
                question=f"What happened in s{i}?",
                answer=f"s{i}_m2",
                evidence_ids=[],
            )
            for i in range(4)
        ],
    )

    lock = threading.Lock()
    per_session_seen: dict[str, list[str]] = {}
    threads_used: set[int] = set()

    class ParallelMockAdapter:
        name = "FAIM-Native"
        system_type = "fractal_graph_memory"

        def is_configured(self):
            return True, None

        def prepare_namespace(self, namespace):
            return None

        def write_memory(self, namespace, memory_id, text, timestamp=None):
            with lock:
                threads_used.add(threading.get_ident())
                session_key = text.split(": ", 1)[1].split("_", 1)[0]
                per_session_seen.setdefault(session_key, []).append(text)
            return IngestOutcome(doc_id=memory_id, latency_ms=1.0, ok=True)

        def query(self, namespace, query_id, query_text, k=20):
            idx = query_id[1:]
            return QueryOutcome(
                query_id=query_id,
                latency_ms=1.0,
                retrieved_doc_ids=[],
                retrieved_texts=[f"s{idx}_m2"],
                answer_text=f"s{idx}_m2",
            )

        def close(self):
            return None

    res = run_conversational_benchmark(
        split=split,
        adapters=[ParallelMockAdapter()],
        top_k=5,
        bootstrap_iterations=10,
        ingest_workers=4,
    )
    sys_out = res["systems"][0]
    assert sys_out["status"] == "completed", sys_out.get("reason")
    assert sys_out["turns_written"] == 12
    assert sys_out["metrics"]["fact_recall"] == 1.0
    for s in range(4):
        assert per_session_seen[f"s{s}"] == [
            f"user: s{s}_m0",
            f"user: s{s}_m1",
            f"user: s{s}_m2",
        ]
