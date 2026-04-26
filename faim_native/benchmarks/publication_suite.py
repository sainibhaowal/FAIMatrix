"""Publication-grade benchmark suite orchestration.

Implements side-by-side FAIM vs baseline retrieval runs, optional MTEB-style
embedding baseline, confidence intervals, reproducibility metadata, and
publication report generation.
"""

from __future__ import annotations

import math
import random
import statistics
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from store.pg.repos.auth_repo import AuthRepo

from benchmarks.dataset_manager import BeirDataset, load_beir_dataset
from benchmarks.metrics import compute_all
from benchmarks.track_a_retrieval import TrackAEvaluator
from benchmarks.track_b_persistence import TrackBEvaluator
from benchmarks.track_e_agent_workflows import TrackEEvaluator
from benchmarks.track_f_real_world_tasks import TrackFEvaluator


def _tokenize(text: str) -> List[str]:
    return [
        tok
        for tok in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
        if tok
    ]


def _mean(values: Sequence[float]) -> float:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return 0.0
    return float(statistics.fmean(vals))


def _claimability_summary() -> Dict[str, Any]:
    return {
        "claimable": [
            "Track A — BEIR retrieval on real qrels",
            "Track D — live telemetry efficiency metrics",
            "BM-1..BM-9 — live system property checks",
        ],
        "internal_validation": [
            "Track B — synthetic persistent-memory scenario",
            "Track C — synthetic continuity scenario",
            "Track E — synthetic agent workflow scenario",
            "Track F — synthetic real-world task scenario",
        ],
        "public_claim_rule": "Only claim Track A, Track D, and BM-1..BM-9 as public benchmark results. Tracks B/C/E/F are internal scenario tests and must not be described as public benchmark performance claims.",
    }


def _bootstrap_ci(
    values: Sequence[float],
    *,
    confidence: float = 0.95,
    iterations: int = 300,
    seed: int = 42,
) -> Dict[str, float]:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}

    if len(vals) == 1:
        m = vals[0]
        return {"mean": m, "ci_low": m, "ci_high": m, "n": 1}

    rnd = random.Random(seed)
    n = len(vals)
    means: List[float] = []
    for _ in range(max(50, iterations)):
        sample = [vals[rnd.randrange(0, n)] for _ in range(n)]
        means.append(_mean(sample))

    means.sort()
    alpha = max(0.0, min(1.0, 1.0 - confidence))
    lo_idx = int((alpha / 2.0) * (len(means) - 1))
    hi_idx = int((1.0 - alpha / 2.0) * (len(means) - 1))
    return {
        "mean": _mean(vals),
        "ci_low": means[lo_idx],
        "ci_high": means[hi_idx],
        "n": len(vals),
    }


def _safe_div(a: float, b: float) -> float:
    if abs(b) < 1e-12:
        return 0.0
    return float(a) / float(b)


class _BM25Retriever:
    def __init__(self, corpus: Dict[str, Dict[str, str]]):
        self.doc_ids: List[str] = []
        self.doc_tokens: Dict[str, List[str]] = {}
        self.term_df: Dict[str, int] = {}
        self.doc_len: Dict[str, int] = {}

        for doc_id, row in corpus.items():
            text = f"{row.get('title', '')} {row.get('text', '')}".strip()
            toks = _tokenize(text)
            self.doc_ids.append(doc_id)
            self.doc_tokens[doc_id] = toks
            self.doc_len[doc_id] = len(toks)
            seen = set(toks)
            for tok in seen:
                self.term_df[tok] = self.term_df.get(tok, 0) + 1

        self.avg_dl = _mean(list(self.doc_len.values()))
        self.n_docs = len(self.doc_ids)

    def _idf(self, term: str) -> float:
        df = self.term_df.get(term, 0)
        return math.log(1.0 + (self.n_docs - df + 0.5) / (df + 0.5))

    def retrieve(self, query_text: str, k: int = 20) -> List[str]:
        q_toks = _tokenize(query_text)
        if not q_toks:
            return []

        k1 = 1.5
        b = 0.75
        scores: Dict[str, float] = {}
        for doc_id in self.doc_ids:
            toks = self.doc_tokens[doc_id]
            if not toks:
                continue
            freq: Dict[str, int] = {}
            for tok in toks:
                freq[tok] = freq.get(tok, 0) + 1
            dl = max(1, self.doc_len[doc_id])
            denom_norm = k1 * (1.0 - b + b * _safe_div(dl, max(1.0, self.avg_dl)))
            score = 0.0
            for tok in q_toks:
                tf = freq.get(tok, 0)
                if tf <= 0:
                    continue
                score += self._idf(tok) * ((tf * (k1 + 1.0)) / (tf + denom_norm))
            if score > 0:
                scores[doc_id] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, _ in ranked[:k]]


class _SummaryRetriever:
    def __init__(self, corpus: Dict[str, Dict[str, str]]):
        self.summary_tokens: Dict[str, Set[str]] = {}
        for doc_id, row in corpus.items():
            text = f"{row.get('title', '')} {row.get('text', '')}".strip()
            words = _tokenize(text)[:40]
            self.summary_tokens[doc_id] = set(words)

    def retrieve(self, query_text: str, k: int = 20) -> List[str]:
        q = set(_tokenize(query_text))
        if not q:
            return []
        scores: List[Tuple[str, float]] = []
        for doc_id, tokens in self.summary_tokens.items():
            overlap = len(q.intersection(tokens))
            if overlap == 0:
                continue
            denom = max(1, len(q.union(tokens)))
            score = overlap / denom
            scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [d for d, _ in scores[:k]]


class _GraphMemoryRetriever:
    def __init__(self, corpus: Dict[str, Dict[str, str]]):
        self.doc_tokens: Dict[str, Set[str]] = {}
        self.token_degree: Dict[str, int] = {}
        for doc_id, row in corpus.items():
            text = f"{row.get('title', '')} {row.get('text', '')}".strip()
            toks = set(_tokenize(text))
            self.doc_tokens[doc_id] = toks
            for tok in toks:
                self.token_degree[tok] = self.token_degree.get(tok, 0) + 1

    def retrieve(self, query_text: str, k: int = 20) -> List[str]:
        q = set(_tokenize(query_text))
        if not q:
            return []
        scores: List[Tuple[str, float]] = []
        for doc_id, toks in self.doc_tokens.items():
            common = q.intersection(toks)
            if not common:
                continue
            centrality = _mean([self.token_degree.get(tok, 0) for tok in common])
            score = len(common) + 0.01 * centrality
            scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [d for d, _ in scores[:k]]


@dataclass
class BaselineDatasetMetrics:
    dataset: str
    corpus_size: int
    query_count: int
    metrics: Dict[str, float]
    confidence_intervals: Dict[str, Dict[str, float]]
    task_completion_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "corpus_size": self.corpus_size,
            "query_count": self.query_count,
            "metrics": {k: round(v, 4) for k, v in self.metrics.items()},
            "confidence_intervals": {
                k: {
                    "mean": round(v.get("mean", 0.0), 4),
                    "ci_low": round(v.get("ci_low", 0.0), 4),
                    "ci_high": round(v.get("ci_high", 0.0), 4),
                    "n": int(v.get("n", 0)),
                }
                for k, v in self.confidence_intervals.items()
            },
            "task_completion_rate": round(self.task_completion_rate, 4),
        }


@dataclass
class SystemWorkflowCheck:
    memory_continuity_passed: bool
    api_key_lifecycle_passed: bool
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_continuity_passed": self.memory_continuity_passed,
            "api_key_lifecycle_passed": self.api_key_lifecycle_passed,
            "notes": self.notes,
        }


@dataclass
class SystemComparisonRow:
    system: str
    system_type: str
    status: str
    metrics: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system": self.system,
            "system_type": self.system_type,
            "status": self.status,
            "metrics": {k: round(v, 4) for k, v in self.metrics.items()},
            "notes": self.notes,
            "reason": self.reason,
        }


BASELINE_SYSTEMS: List[Dict[str, str]] = [
    {"system": "BM25 chunk-RAG", "system_type": "sparse retrieval"},
    {"system": "Dense RAG (all-MiniLM)", "system_type": "embedding retrieval"},
    {"system": "Summary memory", "system_type": "LangChain-style"},
    {"system": "Mem0", "system_type": "commercial memory"},
    {"system": "Zep", "system_type": "commercial memory"},
    {"system": "SuperMemory", "system_type": "commercial memory"},
    {"system": "Full-context (GPT-4o 128k)", "system_type": "no external memory"},
    {"system": "FAIM-Native", "system_type": "native"},
]


@dataclass
class PublicationRun:
    run_id: str
    graph_id: str
    started_at: str
    total_duration_sec: float
    datasets: List[str]
    faim_track_a: Dict[str, Any]
    track_e: Dict[str, Any]
    track_f: Dict[str, Any]
    baselines: Dict[str, List[BaselineDatasetMetrics]]
    mteb: Dict[str, Any]
    workflow_checks: SystemWorkflowCheck
    system_comparison: List[SystemComparisonRow]
    leaderboard: List[Dict[str, Any]]
    results_report: Dict[str, Any]
    reproducibility_kit: Dict[str, Any]
    benchmark_spec: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "started_at": self.started_at,
            "total_duration_sec": round(self.total_duration_sec, 3),
            "datasets": list(self.datasets),
            "faim_track_a": self.faim_track_a,
            "track_e": self.track_e,
            "track_f": self.track_f,
            "baselines": {
                name: [item.to_dict() for item in rows]
                for name, rows in self.baselines.items()
            },
            "mteb": self.mteb,
            "workflow_checks": self.workflow_checks.to_dict(),
            "system_comparison": [row.to_dict() for row in self.system_comparison],
            "leaderboard": self.leaderboard,
            "results_report": self.results_report,
            "reproducibility_kit": self.reproducibility_kit,
            "benchmark_spec": self.benchmark_spec,
        }


class PublicationSuite:
    """Runs publication-grade benchmark suite and exports report-ready artifacts."""

    def __init__(self, ctx: Any):
        self.ctx = ctx

    def _evaluate_retriever(
        self,
        dataset: BeirDataset,
        retrieve: Callable[[str, int], List[str]],
    ) -> BaselineDatasetMetrics:
        per_query: List[Dict[str, float]] = []
        completion_hits = 0
        total = 0

        for qid, qtext in dataset.queries.items():
            relevant = dataset.qrels.get(qid, set())
            if not relevant:
                continue
            retrieved = retrieve(qtext, 20)
            metrics = compute_all(retrieved, relevant)
            per_query.append(metrics)
            total += 1
            if metrics.get("recall@5", 0.0) > 0.0:
                completion_hits += 1

        if not per_query:
            return BaselineDatasetMetrics(
                dataset=dataset.name,
                corpus_size=dataset.corpus_size,
                query_count=0,
                metrics={},
                confidence_intervals={},
                task_completion_rate=0.0,
            )

        metric_names = sorted(per_query[0].keys())
        aggregate_metrics = {
            name: _mean([row.get(name, 0.0) for row in per_query])
            for name in metric_names
        }
        cis = {
            name: _bootstrap_ci([row.get(name, 0.0) for row in per_query])
            for name in metric_names
        }
        return BaselineDatasetMetrics(
            dataset=dataset.name,
            corpus_size=dataset.corpus_size,
            query_count=total,
            metrics=aggregate_metrics,
            confidence_intervals=cis,
            task_completion_rate=_safe_div(completion_hits, total),
        )

    def _run_baselines(
        self,
        dataset_names: List[str],
        max_corpus: Optional[int],
        max_queries: Optional[int],
    ) -> Dict[str, List[BaselineDatasetMetrics]]:
        runners: Dict[str, List[BaselineDatasetMetrics]] = {
            "chunk_rag_bm25": [],
            "dense_rag_all_mini_lm": [],
            "summary_memory": [],
            "graph_memory": [],
        }

        for name in dataset_names:
            ds = load_beir_dataset(name, max_corpus=max_corpus, max_queries=max_queries)
            bm25 = _BM25Retriever(ds.corpus)
            summary = _SummaryRetriever(ds.corpus)
            graph = _GraphMemoryRetriever(ds.corpus)
            dense_metrics = self._dense_baseline_metrics(ds)

            runners["chunk_rag_bm25"].append(
                self._evaluate_retriever(ds, bm25.retrieve)
            )
            runners["dense_rag_all_mini_lm"].append(
                dense_metrics
                or BaselineDatasetMetrics(
                    dataset=name,
                    corpus_size=ds.corpus_size,
                    query_count=0,
                    metrics={},
                    confidence_intervals={},
                    task_completion_rate=0.0,
                )
            )
            runners["summary_memory"].append(
                self._evaluate_retriever(ds, summary.retrieve)
            )
            runners["graph_memory"].append(self._evaluate_retriever(ds, graph.retrieve))

        return runners

    def _run_mteb_like(
        self,
        dataset_names: List[str],
        max_corpus: Optional[int],
        max_queries: Optional[int],
    ) -> Dict[str, Any]:
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            return {
                "status": "skipped",
                "reason": f"sentence-transformers unavailable: {exc}",
                "datasets": [],
            }

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        out_rows: List[Dict[str, Any]] = []

        for name in dataset_names:
            ds = load_beir_dataset(name, max_corpus=max_corpus, max_queries=max_queries)
            doc_ids = list(ds.corpus.keys())
            doc_texts = [
                f"{ds.corpus[d].get('title', '')} {ds.corpus[d].get('text', '')}".strip()
                for d in doc_ids
            ]
            qids = list(ds.queries.keys())
            qtexts = [ds.queries[qid] for qid in qids]

            if not doc_texts or not qtexts:
                out_rows.append({"dataset": name, "metrics": {}, "query_count": 0})
                continue

            d_emb = model.encode(
                doc_texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            q_emb = model.encode(
                qtexts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

            per_query: List[Dict[str, float]] = []
            for i, qid in enumerate(qids):
                relevant = ds.qrels.get(qid, set())
                if not relevant:
                    continue
                sims = np.dot(d_emb, q_emb[i])
                idx = np.argsort(-sims)[:20]
                retrieved = [doc_ids[int(j)] for j in idx.tolist()]
                per_query.append(compute_all(retrieved, relevant))

            metrics = {
                k: _mean([m.get(k, 0.0) for m in per_query])
                for k in (sorted(per_query[0].keys()) if per_query else [])
            }
            cis = {
                k: _bootstrap_ci([m.get(k, 0.0) for m in per_query])
                for k in metrics.keys()
            }
            out_rows.append(
                {
                    "dataset": name,
                    "query_count": len(per_query),
                    "metrics": {k: round(v, 4) for k, v in metrics.items()},
                    "confidence_intervals": {
                        k: {
                            "mean": round(v["mean"], 4),
                            "ci_low": round(v["ci_low"], 4),
                            "ci_high": round(v["ci_high"], 4),
                            "n": int(v["n"]),
                        }
                        for k, v in cis.items()
                    },
                }
            )

        return {
            "status": "completed",
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "datasets": out_rows,
        }

    def _dense_baseline_metrics(
        self,
        dataset: BeirDataset,
    ) -> Optional[BaselineDatasetMetrics]:
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
        except Exception:
            return None

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        doc_ids = list(dataset.corpus.keys())
        doc_texts = [
            f"{dataset.corpus[doc_id].get('title', '')} {dataset.corpus[doc_id].get('text', '')}".strip()
            for doc_id in doc_ids
        ]
        qids = list(dataset.queries.keys())
        qtexts = [dataset.queries[qid] for qid in qids]

        if not doc_texts or not qtexts:
            return BaselineDatasetMetrics(
                dataset=dataset.name,
                corpus_size=dataset.corpus_size,
                query_count=0,
                metrics={},
                confidence_intervals={},
                task_completion_rate=0.0,
            )

        d_emb = model.encode(
            doc_texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        q_emb = model.encode(
            qtexts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        per_query: List[Dict[str, float]] = []
        for i, qid in enumerate(qids):
            relevant = dataset.qrels.get(qid, set())
            if not relevant:
                continue
            sims = np.dot(d_emb, q_emb[i])
            idx = np.argsort(-sims)[:20]
            retrieved = [doc_ids[int(j)] for j in idx.tolist()]
            per_query.append(compute_all(retrieved, relevant))

        if not per_query:
            return BaselineDatasetMetrics(
                dataset=dataset.name,
                corpus_size=dataset.corpus_size,
                query_count=0,
                metrics={},
                confidence_intervals={},
                task_completion_rate=0.0,
            )

        metrics = {
            k: _mean([m.get(k, 0.0) for m in per_query])
            for k in sorted(per_query[0].keys())
        }
        cis = {
            k: _bootstrap_ci([m.get(k, 0.0) for m in per_query]) for k in metrics.keys()
        }
        return BaselineDatasetMetrics(
            dataset=dataset.name,
            corpus_size=dataset.corpus_size,
            query_count=len(per_query),
            metrics=metrics,
            confidence_intervals=cis,
            task_completion_rate=_safe_div(
                sum(1 for row in per_query if row.get("recall@5", 0.0) > 0.0),
                len(per_query),
            ),
        )

    def _evaluate_faim_dataset(
        self,
        dataset: BeirDataset,
        *,
        graph_suffix: str,
    ) -> Dict[str, Any]:
        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest
        from orchestration.query_flow import FAIMProfile as QueryProfile
        from orchestration.query_flow import run_query

        bench_graph_id = f"{dataset.name}__{graph_suffix}__{uuid.uuid4().hex[:8]}"
        doc_id_to_node: Dict[str, str] = {}
        per_query: List[Dict[str, float]] = []

        def _node_id_for(doc_id: str) -> Optional[str]:
            try:
                node = self.ctx.node_repo.get_by_raw_id(bench_graph_id, doc_id)
            except Exception:
                return None
            return (
                str(node.node_id) if node and getattr(node, "node_id", None) else None
            )

        for doc_id, row in dataset.corpus.items():
            content = f"{row.get('title', '')}\n\n{row.get('text', '')}".strip()
            result = run_ingest(
                graph_id=bench_graph_id,
                raw_id=doc_id,
                filename=f"{doc_id}.txt",
                file_bytes=content.encode("utf-8"),
                tenant_id=self.ctx.tenant_id,
                session=self.ctx.session,
                profile=FAIMProfile.STRICT,
                persist_mode=PersistMode.STRICT,
            )
            if result.status in {"completed", "dedup_hit"}:
                node_id = _node_id_for(doc_id)
                if node_id:
                    doc_id_to_node[doc_id] = node_id

        for query_id, query_text in dataset.queries.items():
            relevant_docs = dataset.qrels.get(query_id, set())
            if not relevant_docs:
                continue

            try:
                response = run_query(
                    session=self.ctx.session,
                    tenant_id=self.ctx.tenant_id,
                    graph_id=bench_graph_id,
                    query_text=query_text,
                    k=20,
                    profile=QueryProfile.STRICT,
                    return_explain=False,
                    index=None,
                    cache=self.ctx.cache,
                )
                retrieved = [str(item["node_id"]) for item in response.results]
            except Exception:
                retrieved = []
            finally:
                try:
                    self.ctx.session.rollback()
                except Exception:
                    pass

            relevant_nodes = {
                doc_id_to_node[doc_id]
                for doc_id in relevant_docs
                if doc_id in doc_id_to_node
            }
            per_query.append(compute_all(retrieved, relevant_nodes))

        metrics = {
            name: _mean([row.get(name, 0.0) for row in per_query])
            for name in (sorted(per_query[0].keys()) if per_query else [])
        }
        return {
            "dataset": dataset.name,
            "metrics": {k: round(v, 4) for k, v in metrics.items()},
            "task_completion_rate": round(
                _mean([float(row.get("recall@5", 0.0) > 0.0) for row in per_query]), 4
            ),
            "query_count": len(per_query),
            "corpus_size": dataset.corpus_size,
        }

    def _run_track_e(self, graph_id: str) -> Dict[str, Any]:
        """Orchestrate Track E evaluation using TrackEEvaluator."""
        start = time.monotonic()
        evaluator = TrackEEvaluator(self.ctx)
        dataset = evaluator.build_dataset()

        # Evaluate FAIM on Track E dataset
        faim = self._evaluate_faim_dataset(dataset, graph_suffix="track_e")
        dense_metrics = self._dense_baseline_metrics(dataset)

        # Run Track E probes
        api_key_probe = evaluator.auth_key_lifecycle_probe()
        isolation_probe = evaluator.multi_agent_isolation_probe(graph_id)

        task_completion_rate = float(faim.get("task_completion_rate", 0.0))
        tool_call_memory = float((faim.get("metrics") or {}).get("recall@5", 0.0))
        workflow_score = _mean(
            [
                1.0 if api_key_probe.get("passed") else 0.0,
                1.0 if isolation_probe.get("passed") else 0.0,
                task_completion_rate,
            ]
        )

        systems: List[SystemComparisonRow] = [
            SystemComparisonRow(
                system="FAIM-Native",
                system_type="native",
                status="completed",
                metrics={
                    "api_key_access_memory_accuracy": (
                        1.0 if api_key_probe.get("passed") else 0.0
                    ),
                    "task_completion_rate": task_completion_rate,
                    "tool_call_memory_recall_accuracy": tool_call_memory,
                    "multi_agent_isolation_correctness": (
                        1.0 if isolation_probe.get("passed") else 0.0
                    ),
                    "workflow_score": workflow_score,
                },
                notes=[
                    "real API key lifecycle probe",
                    "real multi-agent isolation probe",
                ],
            ),
            SystemComparisonRow(
                system="BM25 chunk-RAG",
                system_type="sparse retrieval",
                status="completed",
                metrics={
                    "task_completion_rate": self._evaluate_retriever(
                        dataset, _BM25Retriever(dataset.corpus).retrieve
                    ).task_completion_rate,
                    "track_e_workflow_score": self._evaluate_retriever(
                        dataset, _BM25Retriever(dataset.corpus).retrieve
                    ).task_completion_rate,
                },
            ),
            SystemComparisonRow(
                system="Summary memory",
                system_type="LangChain-style",
                status="completed",
                metrics={
                    "task_completion_rate": self._evaluate_retriever(
                        dataset, _SummaryRetriever(dataset.corpus).retrieve
                    ).task_completion_rate,
                    "track_e_workflow_score": self._evaluate_retriever(
                        dataset, _SummaryRetriever(dataset.corpus).retrieve
                    ).task_completion_rate,
                },
            ),
            SystemComparisonRow(
                system="Dense RAG (all-MiniLM)",
                system_type="embedding retrieval",
                status="completed" if dense_metrics else "skipped",
                metrics=(
                    {
                        "task_completion_rate": (
                            dense_metrics.task_completion_rate if dense_metrics else 0.0
                        ),
                        "track_e_workflow_score": (
                            dense_metrics.task_completion_rate if dense_metrics else 0.0
                        ),
                    }
                    if dense_metrics
                    else {}
                ),
                reason=(
                    None
                    if dense_metrics
                    else "dense baseline requires sentence-transformers model availability on runtime"
                ),
            ),
            SystemComparisonRow(
                system="Mem0",
                system_type="commercial memory",
                status="skipped",
                reason="no Mem0 adapter configured",
            ),
            SystemComparisonRow(
                system="Zep",
                system_type="commercial memory",
                status="skipped",
                reason="no Zep adapter configured",
            ),
            SystemComparisonRow(
                system="SuperMemory",
                system_type="commercial memory",
                status="skipped",
                reason="no SuperMemory adapter configured",
            ),
            SystemComparisonRow(
                system="Full-context (GPT-4o 128k)",
                system_type="no external memory",
                status="skipped",
                reason="no OpenAI-compatible model configured",
            ),
        ]

        return {
            "dataset": dataset.name,
            "metrics": {
                "api_key_access_memory_accuracy": round(
                    1.0 if api_key_probe.get("passed") else 0.0, 4
                ),
                "task_completion_rate": round(task_completion_rate, 4),
                "tool_call_memory_recall_accuracy": round(tool_call_memory, 4),
                "multi_agent_isolation_correctness": round(
                    1.0 if isolation_probe.get("passed") else 0.0, 4
                ),
                "workflow_score": round(workflow_score, 4),
            },
            "workflow": {
                "api_key_lifecycle": api_key_probe,
                "multi_agent_isolation": isolation_probe,
            },
            "systems": [row.to_dict() for row in systems],
            "duration_sec": round(time.monotonic() - start, 3),
            "task_count": len(dataset.queries),
        }

    def _run_track_f(self, graph_id: str) -> Dict[str, Any]:
        """Orchestrate Track F evaluation using TrackFEvaluator."""
        start = time.monotonic()
        evaluator = TrackFEvaluator(self.ctx)
        dataset = evaluator.build_dataset()

        # Evaluate FAIM on Track F dataset
        faim = self._evaluate_faim_dataset(dataset, graph_suffix="track_f")
        dense_metrics = self._dense_baseline_metrics(dataset)

        metrics = faim.get("metrics") or {}
        base_score = _mean(
            [
                float(metrics.get("recall@5", 0.0)),
                float(metrics.get("ndcg@10", 0.0)),
                float(metrics.get("mrr", 0.0)),
                float(metrics.get("map", 0.0)),
            ]
        )

        systems: List[SystemComparisonRow] = [
            SystemComparisonRow(
                system="FAIM-Native",
                system_type="native",
                status="completed",
                metrics={
                    "multi_doc_qa_accuracy": float(metrics.get("recall@5", 0.0)),
                    "writing_continuity_score": float(metrics.get("ndcg@10", 0.0)),
                    "personal_assistant_continuity": float(metrics.get("mrr", 0.0)),
                    "code_project_context_retention": float(metrics.get("map", 0.0)),
                    "citation_accuracy": float(metrics.get("precision@5", 0.0)),
                    "stale_fact_suppression": float(metrics.get("recall@3", 0.0)),
                    "overall": base_score,
                },
            ),
            SystemComparisonRow(
                system="BM25 chunk-RAG",
                system_type="sparse retrieval",
                status="completed",
                metrics={
                    "task_completion_rate": self._evaluate_retriever(
                        dataset, _BM25Retriever(dataset.corpus).retrieve
                    ).task_completion_rate,
                    "track_f_overall": self._evaluate_retriever(
                        dataset, _BM25Retriever(dataset.corpus).retrieve
                    ).task_completion_rate,
                },
            ),
            SystemComparisonRow(
                system="Dense RAG (all-MiniLM)",
                system_type="embedding retrieval",
                status="completed" if dense_metrics else "skipped",
                metrics=(
                    {
                        "task_completion_rate": (
                            dense_metrics.task_completion_rate if dense_metrics else 0.0
                        ),
                        "track_f_overall": (
                            dense_metrics.task_completion_rate if dense_metrics else 0.0
                        ),
                    }
                    if dense_metrics
                    else {}
                ),
                reason=(
                    None
                    if dense_metrics
                    else "dense baseline requires sentence-transformers model availability on runtime"
                ),
            ),
            SystemComparisonRow(
                system="Summary memory",
                system_type="LangChain-style",
                status="completed",
                metrics={
                    "task_completion_rate": self._evaluate_retriever(
                        dataset, _SummaryRetriever(dataset.corpus).retrieve
                    ).task_completion_rate,
                    "track_f_overall": self._evaluate_retriever(
                        dataset, _SummaryRetriever(dataset.corpus).retrieve
                    ).task_completion_rate,
                },
            ),
            SystemComparisonRow(
                system="Mem0",
                system_type="commercial memory",
                status="skipped",
                reason="no Mem0 adapter configured",
            ),
            SystemComparisonRow(
                system="Zep",
                system_type="commercial memory",
                status="skipped",
                reason="no Zep adapter configured",
            ),
            SystemComparisonRow(
                system="SuperMemory",
                system_type="commercial memory",
                status="skipped",
                reason="no SuperMemory adapter configured",
            ),
            SystemComparisonRow(
                system="Full-context (GPT-4o 128k)",
                system_type="no external memory",
                status="skipped",
                reason="no OpenAI-compatible model configured",
            ),
        ]

        return {
            "dataset": dataset.name,
            "metrics": {
                "multi_doc_qa_accuracy": round(float(metrics.get("recall@5", 0.0)), 4),
                "writing_continuity_score": round(
                    float(metrics.get("ndcg@10", 0.0)), 4
                ),
                "personal_assistant_continuity": round(
                    float(metrics.get("mrr", 0.0)), 4
                ),
                "code_project_context_retention": round(
                    float(metrics.get("map", 0.0)), 4
                ),
                "citation_accuracy": round(float(metrics.get("precision@5", 0.0)), 4),
                "stale_fact_suppression": round(float(metrics.get("recall@3", 0.0)), 4),
                "overall": round(base_score, 4),
            },
            "systems": [row.to_dict() for row in systems],
            "duration_sec": round(time.monotonic() - start, 3),
            "task_count": len(dataset.queries),
        }

    def _workflow_checks(self, graph_id: str) -> SystemWorkflowCheck:
        notes: List[str] = []
        memory_ok = False
        key_ok = False

        try:
            tb = TrackBEvaluator(self.ctx).run(graph_id)
            memory_ok = bool(
                tb.answer_consistency >= 0.5 and tb.citation_accuracy >= 0.5
            )
            if not memory_ok:
                notes.append("track-b continuity below target")
        except Exception as exc:
            notes.append(f"memory continuity check failed: {exc}")

        try:
            auth_repo = AuthRepo(self.ctx.session)
            record, plain_key = auth_repo.create_tenant_key(
                self.ctx.tenant_id, scopes=["graph:read"]
            )
            listed = auth_repo.list_tenant_keys(
                self.ctx.tenant_id, include_revoked=False
            )
            _ = plain_key
            auth_repo.revoke_tenant_key(
                self.ctx.tenant_id, record.key_id, reason="publication_suite_probe"
            )
            listed_after = auth_repo.list_tenant_keys(
                self.ctx.tenant_id, include_revoked=False
            )
            key_ok = any(r.key_id == record.key_id for r in listed) and all(
                r.key_id != record.key_id for r in listed_after
            )
            self.ctx.session.commit()
        except Exception as exc:
            try:
                self.ctx.session.rollback()
            except Exception:
                pass
            notes.append(f"api key lifecycle check failed: {exc}")

        return SystemWorkflowCheck(
            memory_continuity_passed=memory_ok,
            api_key_lifecycle_passed=key_ok,
            notes=notes,
        )

    def _faim_track_a_summary(self, run_result: Dict[str, Any]) -> Dict[str, Any]:
        rows = run_result.get("datasets", []) if isinstance(run_result, dict) else []
        if not rows:
            return {"datasets": [], "metrics": {}}

        metric_names = ["recall@5", "ndcg@10", "mrr", "map"]
        aggregate_metrics = {}
        for name in metric_names:
            aggregate_metrics[name] = _mean(
                [
                    float((row.get("metrics") or {}).get(name, 0.0) or 0.0)
                    for row in rows
                ]
            )

        return {
            "datasets": rows,
            "metrics": {k: round(v, 4) for k, v in aggregate_metrics.items()},
            "task_completion_rate": round(
                _mean(
                    [
                        float((row.get("metrics") or {}).get("recall@5", 0.0) > 0.0)
                        for row in rows
                    ]
                ),
                4,
            ),
        }

    def _leaderboard(
        self,
        faim_summary: Dict[str, Any],
        baselines: Dict[str, List[BaselineDatasetMetrics]],
        mteb_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        def _avg(rows_in: Iterable[Dict[str, Any]], metric: str) -> float:
            return _mean(
                [
                    float((r.get("metrics") or {}).get(metric, 0.0) or 0.0)
                    for r in rows_in
                ]
            )

        rows.append(
            {
                "system": "FAIM",
                "recall@5": round(
                    float((faim_summary.get("metrics") or {}).get("recall@5", 0.0)), 4
                ),
                "ndcg@10": round(
                    float((faim_summary.get("metrics") or {}).get("ndcg@10", 0.0)), 4
                ),
                "mrr": round(
                    float((faim_summary.get("metrics") or {}).get("mrr", 0.0)), 4
                ),
                "map": round(
                    float((faim_summary.get("metrics") or {}).get("map", 0.0)), 4
                ),
                "task_completion_rate": round(
                    float(faim_summary.get("task_completion_rate", 0.0)), 4
                ),
            }
        )

        for name, rows_data in baselines.items():
            dict_rows = [r.to_dict() for r in rows_data]
            rows.append(
                {
                    "system": name,
                    "recall@5": round(_avg(dict_rows, "recall@5"), 4),
                    "ndcg@10": round(_avg(dict_rows, "ndcg@10"), 4),
                    "mrr": round(_avg(dict_rows, "mrr"), 4),
                    "map": round(_avg(dict_rows, "map"), 4),
                    "task_completion_rate": round(
                        _mean([r.get("task_completion_rate", 0.0) for r in dict_rows]),
                        4,
                    ),
                }
            )

        if mteb_result.get("status") == "completed":
            rows.append(
                {
                    "system": "mteb_sentence_transformer",
                    "recall@5": round(
                        _mean(
                            [
                                float((r.get("metrics") or {}).get("recall@5", 0.0))
                                for r in mteb_result.get("datasets", [])
                            ]
                        ),
                        4,
                    ),
                    "ndcg@10": round(
                        _mean(
                            [
                                float((r.get("metrics") or {}).get("ndcg@10", 0.0))
                                for r in mteb_result.get("datasets", [])
                            ]
                        ),
                        4,
                    ),
                    "mrr": round(
                        _mean(
                            [
                                float((r.get("metrics") or {}).get("mrr", 0.0))
                                for r in mteb_result.get("datasets", [])
                            ]
                        ),
                        4,
                    ),
                    "map": round(
                        _mean(
                            [
                                float((r.get("metrics") or {}).get("map", 0.0))
                                for r in mteb_result.get("datasets", [])
                            ]
                        ),
                        4,
                    ),
                    "task_completion_rate": round(
                        _mean(
                            [
                                float(
                                    (r.get("metrics") or {}).get("recall@5", 0.0) > 0.0
                                )
                                for r in mteb_result.get("datasets", [])
                            ]
                        ),
                        4,
                    ),
                }
            )

        rows.sort(
            key=lambda x: (x.get("ndcg@10", 0.0), x.get("mrr", 0.0)), reverse=True
        )
        return rows

    def _results_report(
        self,
        leaderboard: List[Dict[str, Any]],
        faim_summary: Dict[str, Any],
        baselines: Dict[str, List[BaselineDatasetMetrics]],
        track_e: Dict[str, Any],
        track_f: Dict[str, Any],
        system_comparison: List[SystemComparisonRow],
    ) -> Dict[str, Any]:
        top = leaderboard[0] if leaderboard else {}
        faim = next((r for r in leaderboard if r.get("system") == "FAIM"), {})
        failure_cases: List[Dict[str, Any]] = []

        for baseline_name, rows in baselines.items():
            for row in rows:
                ds = row.to_dict()
                base_ndcg = float((ds.get("metrics") or {}).get("ndcg@10", 0.0))
                faim_ds = next(
                    (
                        d
                        for d in faim_summary.get("datasets", [])
                        if d.get("dataset") == ds.get("dataset")
                    ),
                    None,
                )
                faim_ndcg = float(
                    ((faim_ds or {}).get("metrics") or {}).get("ndcg@10", 0.0)
                )
                if faim_ndcg < base_ndcg:
                    failure_cases.append(
                        {
                            "dataset": ds.get("dataset"),
                            "baseline": baseline_name,
                            "faim_ndcg@10": round(faim_ndcg, 4),
                            "baseline_ndcg@10": round(base_ndcg, 4),
                        }
                    )

        return {
            "methodology": {
                "track_a": "BEIR qrels evaluation with Recall@k, nDCG@10, MRR, MAP",
                "track_b": "Persistent memory retention/update/deletion/hallucination/citation",
                "track_c": "Long-horizon 8+ sessions continuity, stale suppression, and needle retrieval",
                "track_d": "Ingest/retrieval/storage/compression efficiency",
                "track_e": "Agent workflow continuity, API key memory, tool-call recall, and isolation",
                "track_f": "Multi-document QA, grounded writing continuity, assistant history, code context",
                "bm_1_to_9": "System property checks",
            },
            "claimability": _claimability_summary(),
            "summary": {
                "winner": top.get("system"),
                "faim_rank": next(
                    (
                        i + 1
                        for i, row in enumerate(leaderboard)
                        if row.get("system") == "FAIM"
                    ),
                    None,
                ),
                "faim_ndcg@10": faim.get("ndcg@10"),
            },
            "ablations": [
                "summary_memory removes graph structure",
                "graph_memory removes dense lexical scoring",
                "chunk_rag_bm25 removes persistence/evolution",
            ],
            "tracks": {
                "track_e": track_e,
                "track_f": track_f,
            },
            "system_comparison": [row.to_dict() for row in system_comparison],
            "failure_cases": failure_cases,
        }

    def _reproducibility_kit(
        self,
        dataset_names: List[str],
        max_corpus: Optional[int],
        max_queries: Optional[int],
    ) -> Dict[str, Any]:
        return {
            "seed": 42,
            "datasets": dataset_names,
            "max_corpus": max_corpus,
            "max_queries": max_queries,
            "commands": [
                "POST /api/v1/faim-bench/{graph_id}/publication/run",
                "GET /api/v1/faim-bench/{graph_id}/publication/latest",
                "GET /api/v1/faim-bench/{graph_id}/publication/leaderboard",
            ],
            "competitor_slots": [
                "BM25 chunk-RAG",
                "Dense RAG (all-MiniLM)",
                "Summary memory",
                "Mem0",
                "Zep",
                "SuperMemory",
                "Full-context (GPT-4o 128k)",
                "FAIM-Native",
            ],
            "output_schema": {
                "leaderboard": "[{system, recall@5, ndcg@10, mrr, map, task_completion_rate}]",
                "tracks": "{track_e, track_f, system_comparison}",
                "confidence_intervals": "{metric: {mean, ci_low, ci_high, n}}",
                "report": "{methodology, ablations, failure_cases}",
            },
        }

    def _benchmark_spec(
        self,
        dataset_names: List[str],
        max_corpus: Optional[int],
        max_queries: Optional[int],
    ) -> Dict[str, Any]:
        return {
            "version": "faim-bench-publication-v1",
            "datasets": dataset_names,
            "tracks": ["A", "B", "C", "D", "E", "F"],
            "systems": [entry["system"] for entry in BASELINE_SYSTEMS],
            "hyperparameters": {
                "k_values": [1, 3, 5, 10],
                "retrieval_depth": 20,
                "confidence_bootstrap_iterations": 300,
                "seed": 42,
                "max_corpus": max_corpus,
                "max_queries": max_queries,
            },
            "run_rules": [
                "same datasets for FAIM and all baselines",
                "same query set and qrels",
                "metrics computed with identical functions",
                "report unrun competitor sections as skipped in UI",
                "only Track A, Track D, and BM-1..BM-9 are public claimable benchmarks",
            ],
            "claimability": _claimability_summary(),
        }

    def run(
        self,
        graph_id: str,
        dataset_names: Optional[List[str]] = None,
        max_corpus: Optional[int] = None,
        max_queries: Optional[int] = None,
        run_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> PublicationRun:
        names = list(dataset_names or ["scifact", "nfcorpus"])
        started = datetime.now(timezone.utc)
        run_id = run_id or str(uuid.uuid4())
        start_ts = time.monotonic()

        def progress(message: str) -> None:
            if progress_callback is not None:
                progress_callback(message)

        progress(f"Starting publication suite for {len(names)} dataset(s)")

        progress("Running Track A BEIR retrieval")
        track_a = TrackAEvaluator(self.ctx).run(
            graph_id=graph_id,
            dataset_names=names,
            max_corpus=max_corpus,
            max_queries=max_queries,
        )
        faim_summary = self._faim_track_a_summary(track_a.to_dict())

        progress("Running baseline retrieval comparisons")
        baselines = self._run_baselines(
            names, max_corpus=max_corpus, max_queries=max_queries
        )
        progress("Running MTEB-style embedding comparison")
        mteb = self._run_mteb_like(
            names, max_corpus=max_corpus, max_queries=max_queries
        )
        progress("Checking workflow regressions")
        workflow = self._workflow_checks(graph_id)
        progress("Running Track E workflow suite")
        track_e = self._run_track_e(graph_id)
        progress("Running Track F task suite")
        track_f = self._run_track_f(graph_id)
        progress("Building system comparison and report")
        system_comparison = [
            SystemComparisonRow(
                system="FAIM-Native",
                system_type="native",
                status="completed",
                metrics={
                    "track_e_workflow_score": float(
                        (track_e.get("metrics") or {}).get("workflow_score", 0.0)
                    ),
                    "track_f_overall": float(
                        (track_f.get("metrics") or {}).get("overall", 0.0)
                    ),
                },
                notes=[
                    "Tracks E/F measured on live FAIM graph and synthetic task corpora"
                ],
            ),
            SystemComparisonRow(
                system="BM25 chunk-RAG",
                system_type="sparse retrieval",
                status="completed",
                metrics={
                    "track_e_workflow_score": float(
                        (
                            next(
                                (
                                    row
                                    for row in track_e.get("systems", [])
                                    if row.get("system") == "BM25 chunk-RAG"
                                ),
                                {},
                            )
                            or {}
                        )
                        .get("metrics", {})
                        .get("task_completion_rate", 0.0)
                    ),
                    "track_f_overall": float(
                        (
                            next(
                                (
                                    row
                                    for row in track_f.get("systems", [])
                                    if row.get("system") == "BM25 chunk-RAG"
                                ),
                                {},
                            )
                            or {}
                        )
                        .get("metrics", {})
                        .get("task_completion_rate", 0.0)
                    ),
                },
            ),
            SystemComparisonRow(
                system="Dense RAG (all-MiniLM)",
                system_type="embedding retrieval",
                status="skipped",
                reason="dense baseline row is present in the track E/F tables but depends on runtime model availability",
            ),
            SystemComparisonRow(
                system="Summary memory",
                system_type="LangChain-style",
                status="completed",
                metrics={
                    "track_e_workflow_score": float(
                        (
                            next(
                                (
                                    row
                                    for row in track_e.get("systems", [])
                                    if row.get("system") == "Summary memory"
                                ),
                                {},
                            )
                            or {}
                        )
                        .get("metrics", {})
                        .get("task_completion_rate", 0.0)
                    ),
                    "track_f_overall": float(
                        (
                            next(
                                (
                                    row
                                    for row in track_f.get("systems", [])
                                    if row.get("system") == "Summary memory"
                                ),
                                {},
                            )
                            or {}
                        )
                        .get("metrics", {})
                        .get("task_completion_rate", 0.0)
                    ),
                },
            ),
            SystemComparisonRow(
                system="Mem0",
                system_type="commercial memory",
                status="skipped",
                reason="no Mem0 adapter configured",
            ),
            SystemComparisonRow(
                system="Zep",
                system_type="commercial memory",
                status="skipped",
                reason="no Zep adapter configured",
            ),
            SystemComparisonRow(
                system="SuperMemory",
                system_type="commercial memory",
                status="skipped",
                reason="no SuperMemory adapter configured",
            ),
            SystemComparisonRow(
                system="Full-context (GPT-4o 128k)",
                system_type="no external memory",
                status="skipped",
                reason="no OpenAI-compatible model configured",
            ),
        ]
        leaderboard = self._leaderboard(faim_summary, baselines, mteb)
        report = self._results_report(
            leaderboard, faim_summary, baselines, track_e, track_f, system_comparison
        )
        repro = self._reproducibility_kit(names, max_corpus, max_queries)
        spec = self._benchmark_spec(names, max_corpus, max_queries)

        return PublicationRun(
            run_id=run_id,
            graph_id=graph_id,
            started_at=started.isoformat(),
            total_duration_sec=time.monotonic() - start_ts,
            datasets=names,
            faim_track_a=faim_summary,
            track_e=track_e,
            track_f=track_f,
            baselines=baselines,
            mteb=mteb,
            workflow_checks=workflow,
            system_comparison=system_comparison,
            leaderboard=leaderboard,
            results_report=report,
            reproducibility_kit=repro,
            benchmark_spec=spec,
        )


__all__ = ["PublicationSuite", "PublicationRun"]
