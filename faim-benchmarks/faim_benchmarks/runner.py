"""Fair, deterministic benchmark runner with identical splits and bootstrap CIs."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from faim_benchmarks.adapters.base import MemorySystemAdapter
from faim_benchmarks.datasets import ConversationalBenchmarkSplit, RetrievalBenchmarkSplit
from faim_benchmarks.metrics import (
    answer_contains_gold,
    bootstrap_ci,
    compute_ir_metrics,
    exact_match,
    percentile,
    token_f1,
)


def _skipped_system(adapter: MemorySystemAdapter, reason: str) -> Dict[str, Any]:
    return {
        "system": adapter.name,
        "system_type": adapter.system_type,
        "status": "skipped",
        "reason": reason,
        "metrics": {},
        "confidence_intervals": {},
        "latency_ms": {},
    }


def _failed_system(
    adapter: MemorySystemAdapter,
    reason: str,
    **details: Any,
) -> Dict[str, Any]:
    """Represent an adapter failure without converting it into a score."""
    return {
        "system": adapter.name,
        "system_type": adapter.system_type,
        "status": "failed",
        "reason": reason[:500],
        "metrics": {},
        "confidence_intervals": {},
        "latency_ms": {},
        **details,
    }


def _exception_reason(exc: Exception) -> str:
    message = str(exc).strip()
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def run_retrieval_benchmark(
    *,
    split: RetrievalBenchmarkSplit,
    adapters: Sequence[MemorySystemAdapter],
    top_k: int = 20,
    seed: int = 42,
    bootstrap_iterations: int = 300,
    ingest_workers: int = 1,
    run_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run an identical BEIR retrieval split across every configured adapter."""
    if not split.queries:
        raise ValueError("Retrieval benchmark split has no queries")

    run_id = f"ret_{split.name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    systems_out: List[Dict[str, Any]] = []

    for adapter in adapters:
        try:
            ok, reason = adapter.is_configured()
        except Exception as exc:
            systems_out.append(_failed_system(adapter, _exception_reason(exc)))
            continue
        if not ok:
            systems_out.append(_skipped_system(adapter, reason or "Not configured"))
            continue

        namespace = f"{run_id}_{adapter.name.lower().replace(' ', '_')}"
        try:
            adapter.prepare_namespace(namespace)
        except Exception as exc:
            systems_out.append(_failed_system(adapter, _exception_reason(exc), namespace=namespace))
            continue

        ingest_latencies: List[float] = []
        ingest_errors = 0
        ingest_failures: List[str] = []

        def _ingest_one(item: tuple[str, Dict[str, str]]) -> tuple[str, Any, Optional[Exception]]:
            doc_id, doc = item
            try:
                res = adapter.ingest_document(
                    namespace, doc_id, doc.get("title", ""), doc.get("text", "")
                )
                return doc_id, res, None
            except Exception as exc:
                return doc_id, None, exc

        items = list(split.corpus.items())
        worker_count = max(1, int(ingest_workers))
        batch_ingester = getattr(adapter, "ingest_documents_batch", None)
        if callable(batch_ingester) and getattr(adapter, "batch_size", 0) > 1:
            batch_size = int(getattr(adapter, "batch_size"))
            batches = [items[start : start + batch_size] for start in range(0, len(items), batch_size)]

            def _ingest_batch(batch):
                try:
                    return batch, batch_ingester(namespace, batch), None
                except Exception as exc:
                    return batch, None, exc

            if worker_count == 1:
                batch_outcomes = (_ingest_batch(batch) for batch in batches)
            else:
                pool = ThreadPoolExecutor(max_workers=worker_count)
                batch_outcomes = pool.map(_ingest_batch, batches)
            outcomes = []
            for batch, batch_results, batch_exc in batch_outcomes:
                if batch_exc is not None:
                    outcomes.extend((doc_id, None, batch_exc) for doc_id, _ in batch)
                    continue
                outcomes.extend((doc_id, res, None) for (doc_id, _), res in zip(batch, batch_results))
            if worker_count > 1:
                pool.shutdown()
            outcomes = iter(outcomes)
            for doc_id, res, exc in outcomes:
                if exc is not None:
                    ingest_failures.append(f"{doc_id}: {_exception_reason(exc)}")
                    continue
                ingest_latencies.append(res.latency_ms)
                if not res.ok:
                    ingest_errors += 1
                    if res.error:
                        ingest_failures.append(f"{doc_id}: {res.error}")
        elif worker_count == 1:
            outcomes = (_ingest_one(item) for item in items)
            for doc_id, res, exc in outcomes:
                if exc is not None:
                    ingest_failures.append(f"{doc_id}: {_exception_reason(exc)}")
                    continue
                ingest_latencies.append(res.latency_ms)
                if not res.ok:
                    ingest_errors += 1
                    if res.error:
                        ingest_failures.append(f"{doc_id}: {res.error}")
        else:
            with ThreadPoolExecutor(max_workers=worker_count) as pool:
                outcomes = pool.map(_ingest_one, items)
                for doc_id, res, exc in outcomes:
                    if exc is not None:
                        ingest_failures.append(f"{doc_id}: {_exception_reason(exc)}")
                        continue
                    ingest_latencies.append(res.latency_ms)
                    if not res.ok:
                        ingest_errors += 1
                        if res.error:
                            ingest_failures.append(f"{doc_id}: {res.error}")

        if ingest_errors or ingest_failures or len(ingest_latencies) != len(split.corpus):
            systems_out.append(
                _failed_system(
                    adapter,
                    f"{ingest_errors + len(ingest_failures)} ingest operation(s) failed"
                    + (f": {ingest_failures[0]}" if ingest_failures else ""),
                    namespace=namespace,
                    corpus_docs=len(split.corpus),
                    ingest_errors=ingest_errors + len(ingest_failures),
                )
            )
            continue

        query_latencies: List[float] = []
        per_query_scores: Dict[str, List[float]] = {
            "recall@5": [],
            "recall@10": [],
            "precision@5": [],
            "ndcg@10": [],
            "mrr": [],
            "map": [],
        }

        for qid, qtext in split.queries.items():
            try:
                qres = adapter.query(namespace, qid, qtext, k=top_k)
            except Exception as exc:
                systems_out.append(
                    _failed_system(
                        adapter,
                        f"Query failed for {qid}: {_exception_reason(exc)}",
                        namespace=namespace,
                        corpus_docs=len(split.corpus),
                        queries_evaluated=len(query_latencies),
                        ingest_errors=ingest_errors,
                    )
                )
                break
            query_latencies.append(qres.latency_ms)
            ir = compute_ir_metrics(qres.retrieved_doc_ids, split.qrels.get(qid, {}), k_values=(1, 3, 5, 10))
            for metric_name in per_query_scores:
                per_query_scores[metric_name].append(ir[metric_name])

        if len(query_latencies) != len(split.queries):
            continue

        cis = {
            metric_name: bootstrap_ci(vals, iterations=bootstrap_iterations, seed=seed)
            for metric_name, vals in per_query_scores.items()
        }
        agg_metrics = {metric_name: ci["mean"] for metric_name, ci in cis.items()}

        systems_out.append(
            {
                "system": adapter.name,
                "system_type": adapter.system_type,
                "status": "completed",
                "namespace": namespace,
                "corpus_docs": len(split.corpus),
                "queries_evaluated": len(split.queries),
                "ingest_errors": ingest_errors,
                "metrics": agg_metrics,
                "confidence_intervals": cis,
                "latency_ms": {
                    "ingest_p50": percentile(ingest_latencies, 50),
                    "ingest_p95": percentile(ingest_latencies, 95),
                    "query_p50": percentile(query_latencies, 50),
                    "query_p95": percentile(query_latencies, 95),
                    "query_p99": percentile(query_latencies, 99),
                },
            }
        )

    return {
        "run_id": run_id,
        "suite_type": "retrieval_beir",
        "dataset": split.name,
        "dataset_metadata": getattr(split, "metadata", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_metadata": run_metadata or {},
        "hyperparameters": {
            "top_k": top_k,
            "seed": seed,
            "bootstrap_iterations": bootstrap_iterations,
            "ingest_workers": max(1, int(ingest_workers)),
            "corpus_size": len(split.corpus),
            "query_count": len(split.queries),
        },
        "systems": systems_out,
    }


def run_conversational_benchmark(
    *,
    split: ConversationalBenchmarkSplit,
    adapters: Sequence[MemorySystemAdapter],
    top_k: int = 20,
    seed: int = 42,
    bootstrap_iterations: int = 300,
    run_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run LoCoMo or LongMemEval across all configured memory adapters."""
    if not split.qa_cases:
        raise ValueError("Conversational benchmark split has no QA cases")

    run_id = f"mem_{split.name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    systems_out: List[Dict[str, Any]] = []

    for adapter in adapters:
        try:
            ok, reason = adapter.is_configured()
        except Exception as exc:
            systems_out.append(_failed_system(adapter, _exception_reason(exc)))
            continue
        if not ok:
            systems_out.append(_skipped_system(adapter, reason or "Not configured"))
            continue

        namespace = f"{run_id}_{adapter.name.lower().replace(' ', '_')}"
        try:
            adapter.prepare_namespace(namespace)
        except Exception as exc:
            systems_out.append(_failed_system(adapter, _exception_reason(exc), namespace=namespace))
            continue

        write_latencies: List[float] = []
        write_errors = 0
        for idx, turn in enumerate(split.turns):
            mem_id = f"turn_{idx}"
            text = f"{turn.speaker}: {turn.text}"
            try:
                res = adapter.write_memory(namespace, mem_id, text, timestamp=turn.timestamp)
            except Exception as exc:
                systems_out.append(
                    _failed_system(
                        adapter,
                        f"Write failed for {mem_id}: {_exception_reason(exc)}",
                        namespace=namespace,
                        turns_written=idx,
                        write_errors=write_errors + 1,
                    )
                )
                break
            write_latencies.append(res.latency_ms)
            if not res.ok:
                write_errors += 1

        if write_errors or len(write_latencies) != len(split.turns):
            if not systems_out or systems_out[-1].get("namespace") != namespace:
                systems_out.append(
                    _failed_system(
                        adapter,
                        f"{write_errors} write operation(s) failed",
                        namespace=namespace,
                        turns_written=len(write_latencies),
                        write_errors=write_errors,
                    )
                )
            continue

        query_latencies: List[float] = []
        per_case: Dict[str, List[float]] = {"exact_match": [], "token_f1": [], "fact_recall": []}

        for case in split.qa_cases:
            try:
                qres = adapter.query(namespace, case.case_id, case.question, k=top_k)
            except Exception as exc:
                systems_out.append(
                    _failed_system(
                        adapter,
                        f"Query failed for {case.case_id}: {_exception_reason(exc)}",
                        namespace=namespace,
                        turns_written=len(split.turns),
                        cases_evaluated=len(per_case["exact_match"]),
                        write_errors=write_errors,
                    )
                )
                break
            query_latencies.append(qres.latency_ms)
            combined_ctx = qres.answer_text or "\n".join(qres.retrieved_texts)
            per_case["exact_match"].append(exact_match(qres.answer_text, case.answer))
            per_case["token_f1"].append(token_f1(qres.answer_text, case.answer))
            per_case["fact_recall"].append(answer_contains_gold(combined_ctx, case.answer))

        if len(query_latencies) != len(split.qa_cases):
            continue

        cis = {
            metric_name: bootstrap_ci(vals, iterations=bootstrap_iterations, seed=seed)
            for metric_name, vals in per_case.items()
        }
        systems_out.append(
            {
                "system": adapter.name,
                "system_type": adapter.system_type,
                "status": "completed",
                "namespace": namespace,
                "turns_written": len(split.turns),
                "cases_evaluated": len(split.qa_cases),
                "write_errors": write_errors,
                "metrics": {m: ci["mean"] for m, ci in cis.items()},
                "confidence_intervals": cis,
                "latency_ms": {
                    "write_p50": percentile(write_latencies, 50),
                    "write_p95": percentile(write_latencies, 95),
                    "query_p50": percentile(query_latencies, 50),
                    "query_p95": percentile(query_latencies, 95),
                },
            }
        )

    return {
        "run_id": run_id,
        "suite_type": "conversational_memory",
        "dataset": split.name,
        "dataset_metadata": getattr(split, "metadata", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_metadata": run_metadata or {},
        "hyperparameters": {
            "top_k": top_k,
            "seed": seed,
            "bootstrap_iterations": bootstrap_iterations,
            "turn_count": len(split.turns),
            "qa_count": len(split.qa_cases),
        },
        "systems": systems_out,
    }
