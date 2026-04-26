"""Track A — Retrieval Quality (BEIR-compatible).

Downloads BEIR datasets from HuggingFace, ingests each corpus into a
fresh FAIM sub-graph, queries with all test queries, evaluates against
ground-truth relevance judgments.

Metrics: Recall@5, Recall@10, Precision@5, nDCG@10, MRR, MAP
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

from benchmarks.dataset_manager import BeirDataset, load_beir_dataset
from benchmarks.metrics import aggregate, compute_all

logger = logging.getLogger(__name__)

# Default datasets to run (ordered small → large)
DEFAULT_DATASETS = ["scifact", "nfcorpus"]


@dataclass
class DatasetResult:
    dataset: str
    corpus_size: int
    query_count: int
    metrics: Dict[str, float]
    ingest_duration_sec: float
    eval_duration_sec: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "corpus_size": self.corpus_size,
            "query_count": self.query_count,
            "metrics": {k: round(v, 4) for k, v in self.metrics.items()},
            "ingest_duration_sec": round(self.ingest_duration_sec, 1),
            "eval_duration_sec": round(self.eval_duration_sec, 1),
            "error": self.error,
        }


@dataclass
class TrackAResult:
    run_id: str
    graph_id: str
    datasets: List[DatasetResult]
    total_duration_sec: float
    status: str = "completed"  # "running" | "completed" | "failed"
    progress_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "status": self.status,
            "progress_message": self.progress_message,
            "total_duration_sec": round(self.total_duration_sec, 1),
            "datasets": [d.to_dict() for d in self.datasets],
        }


# In-memory job store for background runs
_jobs: Dict[str, TrackAResult] = {}
_jobs_lock = threading.Lock()


def get_job(job_id: str) -> Optional[TrackAResult]:
    with _jobs_lock:
        return _jobs.get(job_id)


def list_jobs() -> List[TrackAResult]:
    with _jobs_lock:
        return list(_jobs.values())


class TrackAEvaluator:
    """Run Track A — BEIR retrieval evaluation against a live FAIM graph."""

    def __init__(self, ctx: Any):
        self.ctx = ctx

    def _ingest_corpus(
        self,
        bench_graph_id: str,
        corpus: Dict[str, Dict],
        progress_cb: Callable[[str], None],
    ) -> Dict[str, Optional[str]]:
        """Ingest corpus documents into FAIM. Returns doc_id → node_id mapping."""
        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest

        doc_id_to_node: Dict[str, Optional[str]] = {}
        total = len(corpus)
        batch_errors = 0

        def _node_id_for(doc_id: str) -> Optional[str]:
            try:
                node = self.ctx.node_repo.get_by_raw_id(bench_graph_id, doc_id)
            except Exception:
                return None
            return (
                str(node.node_id) if node and getattr(node, "node_id", None) else None
            )

        for i, (doc_id, doc) in enumerate(corpus.items()):
            title = doc.get("title", "")
            text = doc.get("text", "")
            content = f"{title}\n\n{text}".strip() if title else text

            try:
                result = run_ingest(
                    graph_id=bench_graph_id,
                    raw_id=f"beir_{doc_id}",
                    filename=f"beir_{doc_id}.txt",
                    file_bytes=content.encode("utf-8"),
                    tenant_id=self.ctx.tenant_id,
                    session=self.ctx.session,
                    profile=FAIMProfile.STRICT,
                    persist_mode=PersistMode.STRICT,
                )
                if result.status in {"completed", "dedup_hit"}:
                    doc_id_to_node[doc_id] = _node_id_for(doc_id)
                else:
                    doc_id_to_node[doc_id] = None
            except Exception as exc:
                batch_errors += 1
                doc_id_to_node[doc_id] = None
                if batch_errors <= 3:
                    logger.warning("ingest failed doc=%s: %s", doc_id, exc)
                try:
                    self.ctx.session.rollback()
                except Exception:
                    pass

            if (i + 1) % 50 == 0 or (i + 1) == total:
                progress_cb(
                    f"Ingested {i + 1}/{total} documents ({batch_errors} errors)"
                )

        return doc_id_to_node

    def _build_node_to_docs(
        self,
        bench_graph_id: str,
        doc_id_to_node: Dict[str, Optional[str]],
    ) -> Dict[str, List[str]]:
        """Invert mapping: node_id → [doc_ids].
        One node can represent multiple docs if FAIM deduplication merged them."""
        node_to_docs: Dict[str, List[str]] = {}
        for doc_id, node_id in doc_id_to_node.items():
            if node_id:
                node_to_docs.setdefault(node_id, []).append(doc_id)
        return node_to_docs

    def _query_faim(
        self, bench_graph_id: str, query_text: str, k: int = 20
    ) -> List[str]:
        """Run a FAIM query and return retrieved node IDs (rolled back)."""
        from orchestration.query_flow import FAIMProfile, run_query

        try:
            result = run_query(
                session=self.ctx.session,
                tenant_id=self.ctx.tenant_id,
                graph_id=bench_graph_id,
                query_text=query_text,
                k=k,
                profile=FAIMProfile.STRICT,
                return_explain=False,
                index=None,
                cache=self.ctx.cache,
            )
            retrieved = [str(r["node_id"]) for r in result.results]
            return retrieved
        except Exception as exc:
            logger.warning("query failed: %s", exc)
            return []
        finally:
            try:
                self.ctx.session.rollback()
            except Exception:
                pass

    def _evaluate_dataset(
        self,
        dataset: BeirDataset,
        progress_cb: Callable[[str], None],
    ) -> DatasetResult:
        bench_graph_id = f"beir_{dataset.name}_{self.ctx.tenant_id}"

        # Ingest
        ingest_start = time.monotonic()
        progress_cb(
            f"[{dataset.name}] Starting ingestion of {dataset.corpus_size} documents..."
        )
        doc_id_to_node = self._ingest_corpus(
            bench_graph_id, dataset.corpus, progress_cb
        )
        ingest_duration = time.monotonic() - ingest_start
        node_to_docs = self._build_node_to_docs(bench_graph_id, doc_id_to_node)

        ingested_count = sum(1 for v in doc_id_to_node.values() if v is not None)
        progress_cb(
            f"[{dataset.name}] Ingestion complete: {ingested_count}/{dataset.corpus_size} docs in {ingest_duration:.0f}s. Running {dataset.query_count} queries..."
        )

        # Evaluate
        eval_start = time.monotonic()
        per_query: List[Dict[str, float]] = []

        for i, (query_id, query_text) in enumerate(dataset.queries.items()):
            relevant_doc_ids: Set[str] = dataset.qrels.get(query_id, set())
            if not relevant_doc_ids:
                continue

            retrieved_node_ids = self._query_faim(bench_graph_id, query_text, k=20)

            # Expand node IDs to doc IDs (handles FAIM deduplication)
            retrieved_doc_ids: List[str] = []
            seen: Set[str] = set()
            for node_id in retrieved_node_ids:
                for doc_id in node_to_docs.get(node_id, []):
                    if doc_id not in seen:
                        retrieved_doc_ids.append(doc_id)
                        seen.add(doc_id)

            per_query.append(compute_all(retrieved_doc_ids, relevant_doc_ids))

            if (i + 1) % 50 == 0:
                progress_cb(
                    f"[{dataset.name}] Evaluated {i + 1}/{dataset.query_count} queries"
                )

        eval_duration = time.monotonic() - eval_start
        agg = aggregate(per_query) if per_query else {}
        progress_cb(f"[{dataset.name}] Done. nDCG@10={agg.get('ndcg@10', 0):.3f}")

        return DatasetResult(
            dataset=dataset.name,
            corpus_size=dataset.corpus_size,
            query_count=len(per_query),
            metrics=agg,
            ingest_duration_sec=ingest_duration,
            eval_duration_sec=eval_duration,
        )

    def run(
        self,
        graph_id: str,
        dataset_names: Optional[List[str]] = None,
        max_corpus: Optional[int] = None,
        max_queries: Optional[int] = None,
    ) -> TrackAResult:
        """Run Track A synchronously. Prefer start_background for long runs."""
        run_id = str(uuid.uuid4())
        names = dataset_names or DEFAULT_DATASETS
        start = time.monotonic()
        results: List[DatasetResult] = []

        job = TrackAResult(
            run_id=run_id,
            graph_id=graph_id,
            datasets=results,
            total_duration_sec=0.0,
            status="running",
        )
        with _jobs_lock:
            _jobs[run_id] = job

        def progress(msg: str) -> None:
            job.progress_message = msg
            logger.info("track-a: %s", msg)

        try:
            for name in names:
                try:
                    dataset = load_beir_dataset(
                        name, max_corpus=max_corpus, max_queries=max_queries
                    )
                    result = self._evaluate_dataset(dataset, progress)
                    results.append(result)
                except Exception as exc:
                    logger.exception("track-a dataset=%s failed", name)
                    results.append(
                        DatasetResult(
                            dataset=name,
                            corpus_size=0,
                            query_count=0,
                            metrics={},
                            ingest_duration_sec=0,
                            eval_duration_sec=0,
                            error=str(exc),
                        )
                    )
        finally:
            job.total_duration_sec = time.monotonic() - start
            job.status = "completed"
            job.progress_message = (
                f"Completed {len(results)} datasets in {job.total_duration_sec:.0f}s"
            )

        return job

    def start_background(
        self,
        graph_id: str,
        dataset_names: Optional[List[str]] = None,
        max_corpus: Optional[int] = None,
        max_queries: Optional[int] = None,
    ) -> str:
        """Start Track A evaluation in background thread. Returns job_id."""
        run_id = str(uuid.uuid4())
        job = TrackAResult(
            run_id=run_id,
            graph_id=graph_id,
            datasets=[],
            total_duration_sec=0.0,
            status="running",
            progress_message="Starting...",
        )
        with _jobs_lock:
            _jobs[run_id] = job

        def _run():
            names = dataset_names or DEFAULT_DATASETS
            start = time.monotonic()

            def progress(msg: str) -> None:
                job.progress_message = msg
                logger.info("track-a bg: %s", msg)

            try:
                for name in names:
                    try:
                        dataset = load_beir_dataset(
                            name, max_corpus=max_corpus, max_queries=max_queries
                        )
                        result = self._evaluate_dataset(dataset, progress)
                        job.datasets.append(result)
                    except Exception as exc:
                        logger.exception("track-a bg dataset=%s failed", name)
                        job.datasets.append(
                            DatasetResult(
                                dataset=name,
                                corpus_size=0,
                                query_count=0,
                                metrics={},
                                ingest_duration_sec=0,
                                eval_duration_sec=0,
                                error=str(exc),
                            )
                        )
            finally:
                job.total_duration_sec = time.monotonic() - start
                job.status = "completed"
                job.progress_message = f"Completed {len(job.datasets)} datasets"

        t = threading.Thread(target=_run, daemon=True, name=f"track-a-{run_id[:8]}")
        t.start()
        return run_id
