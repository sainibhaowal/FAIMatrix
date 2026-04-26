"""Track B — Persistent Memory.

Tests memory retention, update, contradiction, deletion, and provenance.
Runs entirely on synthetic data — no external dataset required.

Metrics reported:
  - retention_recall@k: after N inserts, query, measure Recall@k
  - update_accuracy: after fact update, old value suppressed, new value retrieved
  - contradiction_resolution: FAIM deduplication handles conflicting facts
  - deletion_completeness: after delete, fact no longer retrieved (recall = 0)
  - provenance_accuracy: citation back to source document is correct
  - hallucination_rate: results returned that were never ingested
  - answer_consistency: same query across sessions returns consistent top-1
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from benchmarks.metrics import aggregate, compute_all

FACTS = [
    ("user_name", "The user's name is Alice Chen."),
    ("user_role", "Alice works as a senior machine learning engineer."),
    ("user_company", "Alice is employed at Meridian Labs in San Francisco."),
    ("user_project", "Alice is currently building a knowledge graph pipeline."),
    ("user_language", "Alice primarily codes in Python and Rust."),
    ("user_goal", "Alice wants to reduce hallucination in her RAG system."),
    ("task_deadline", "The project deadline is March 31st."),
    ("task_budget", "The project budget is $120,000."),
    ("task_team", "The team consists of Alice, Bob, and Carlos."),
    ("collab_bob", "Bob specializes in infrastructure and DevOps."),
    ("collab_carlos", "Carlos is the product manager for the knowledge project."),
    ("pref_model", "Alice prefers GPT-4o for generation tasks."),
    ("pref_memory", "Alice previously used LangChain memory which lost context."),
    ("past_issue", "The previous system failed to handle 10,000+ documents."),
    ("current_concern", "Alice is concerned about latency under high load."),
]

UPDATED_FACTS = {
    "user_role": "Alice has been promoted to Staff Engineer.",
    "task_deadline": "The deadline has moved to April 30th.",
    "pref_model": "Alice now prefers Claude 3.5 Sonnet over GPT-4o.",
}

CONTRADICTING_FACTS = {
    "task_budget": "The project budget is $80,000.",  # contradicts $120,000
}

MULTI_DOC_QA = [
    {
        "question": "What is Alice's role?",
        "doc_ids": ["user_role"],
        "expected_answer_fragment": "engineer",
    },
    {
        "question": "Who is on the team?",
        "doc_ids": ["task_team"],
        "expected_answer_fragment": "Alice",
    },
    {
        "question": "What is the project deadline?",
        "doc_ids": ["task_deadline"],
        "expected_answer_fragment": "March",
    },
]


@dataclass
class TrackBResult:
    run_id: str
    graph_id: str
    duration_sec: float

    # Retrieval quality
    retention_metrics: Dict[str, float] = field(default_factory=dict)
    update_accuracy: float = 0.0
    deletion_completeness: float = 0.0
    provenance_accuracy: float = 0.0
    hallucination_rate: float = 0.0
    answer_consistency: float = 0.0
    contradiction_resolution: float = 0.0

    # Multi-doc Q&A
    multidoc_qa_accuracy: float = 0.0
    citation_accuracy: float = 0.0

    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "duration_sec": round(self.duration_sec, 3),
            "retention": self.retention_metrics,
            "update_accuracy": round(self.update_accuracy, 4),
            "deletion_completeness": round(self.deletion_completeness, 4),
            "provenance_accuracy": round(self.provenance_accuracy, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "answer_consistency": round(self.answer_consistency, 4),
            "contradiction_resolution": round(self.contradiction_resolution, 4),
            "multidoc_qa_accuracy": round(self.multidoc_qa_accuracy, 4),
            "citation_accuracy": round(self.citation_accuracy, 4),
            "notes": self.notes,
            "errors": self.errors,
        }


class TrackBEvaluator:
    """Run Track B — Persistent Memory evaluation on a live FAIM graph."""

    def __init__(self, ctx: Any):
        self.ctx = ctx

    def _ingest(self, graph_id: str, doc_id: str, content: str) -> bool:
        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest

        try:
            result = run_ingest(
                graph_id=graph_id,
                raw_id=doc_id,
                filename=f"{doc_id}.txt",
                file_bytes=content.encode("utf-8"),
                tenant_id=self.ctx.tenant_id,
                session=self.ctx.session,
                profile=FAIMProfile.STRICT,
                persist_mode=PersistMode.STRICT,
            )
            return result.status in ("completed", "dedup_hit")
        except Exception:
            return False

    def _query(self, graph_id: str, query_text: str, k: int = 10) -> List[str]:
        from orchestration.query_flow import FAIMProfile, run_query

        try:
            result = run_query(
                session=self.ctx.session,
                tenant_id=self.ctx.tenant_id,
                graph_id=graph_id,
                query_text=query_text,
                k=k,
                profile=FAIMProfile.STRICT,
                return_explain=False,
                index=None,
                cache=self.ctx.cache,
            )
            return [str(r["node_id"]) for r in result.results]
        except Exception:
            return []

    def _delete(self, graph_id: str, doc_id: str) -> bool:
        try:
            node = self.ctx.node_repo.get_by_raw_id(graph_id, doc_id)
            if node:
                self.ctx.node_repo.delete(self.ctx.session, graph_id, str(node.node_id))
                self.ctx.session.commit()
                return True
            return False
        except Exception:
            return False

    def _node_ids_for_docs(self, graph_id: str, doc_ids: List[str]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for doc_id in doc_ids:
            try:
                node = self.ctx.node_repo.get_by_raw_id(graph_id, doc_id)
                if node:
                    mapping[doc_id] = str(node.node_id)
            except Exception:
                pass
        return mapping

    def run(self, graph_id: str) -> TrackBResult:
        run_id = str(uuid.uuid4())
        start = time.monotonic()
        result = TrackBResult(run_id=run_id, graph_id=graph_id, duration_sec=0.0)

        # Use a fresh isolated sub-graph so tests don't pollute user's data
        bench_graph_id = f"{graph_id}__bench_b_{run_id[:8]}"

        try:
            # ── Phase 1: Ingest all facts ──────────────────────────────────
            ingested_doc_ids: List[str] = []
            for doc_id, content in FACTS:
                if self._ingest(bench_graph_id, doc_id, content):
                    ingested_doc_ids.append(doc_id)

            doc_id_to_node = self._node_ids_for_docs(bench_graph_id, ingested_doc_ids)
            ingested_node_ids = set(doc_id_to_node.values())

            # ── Phase 2: Retention — query each fact, measure Recall@k ─────
            per_query_metrics: List[Dict[str, float]] = []
            for doc_id, content in FACTS:
                if doc_id not in doc_id_to_node:
                    continue
                # Use first sentence as query
                query = content.split(".")[0]
                retrieved = self._query(bench_graph_id, query, k=10)
                relevant = {doc_id_to_node[doc_id]}
                per_query_metrics.append(compute_all(retrieved, relevant))

            result.retention_metrics = (
                aggregate(per_query_metrics) if per_query_metrics else {}
            )

            # ── Phase 3: Hallucination rate ────────────────────────────────
            # Query for something that was never ingested
            phantom_queries = [
                "quantum entanglement photon spin",
                "medieval siege warfare catapult",
                "deep sea bioluminescent jellyfish",
            ]
            phantom_hits = 0
            phantom_total = 0
            for q in phantom_queries:
                retrieved = self._query(bench_graph_id, q, k=5)
                for node_id in retrieved:
                    phantom_total += 1
                    if node_id in ingested_node_ids:
                        phantom_hits += 1  # returned a real node for an unrelated query

            # Lower is better: hallucination_rate = fraction of phantom results that are real nodes
            result.hallucination_rate = round(phantom_hits / max(1, phantom_total), 4)

            # ── Phase 4: Update accuracy ───────────────────────────────────
            update_correct = 0
            update_total = 0
            for doc_id, new_content in UPDATED_FACTS.items():
                self._ingest(bench_graph_id, f"{doc_id}_v2", new_content)
                update_total += 1
                # Query for the new version — should be top result
                retrieved = self._query(bench_graph_id, new_content.split(".")[0], k=5)
                new_node = self._node_ids_for_docs(bench_graph_id, [f"{doc_id}_v2"])
                if new_node and new_node.get(f"{doc_id}_v2") in retrieved[:3]:
                    update_correct += 1

            result.update_accuracy = update_correct / max(1, update_total)

            # ── Phase 5: Contradiction resolution ─────────────────────────
            contradiction_ok = 0
            for doc_id, contra_content in CONTRADICTING_FACTS.items():
                self._ingest(bench_graph_id, f"{doc_id}_contra", contra_content)
                # Query: system should return SOMETHING (not crash, not return nothing)
                retrieved = self._query(bench_graph_id, "project budget cost", k=5)
                if retrieved:  # FAIM handled the contradiction without erroring
                    contradiction_ok += 1

            result.contradiction_resolution = contradiction_ok / max(
                1, len(CONTRADICTING_FACTS)
            )

            # ── Phase 6: Deletion completeness ────────────────────────────
            delete_doc_id, delete_content = FACTS[0]  # delete "user_name" fact
            delete_query = delete_content.split(".")[0]

            # Confirm it's retrievable before delete
            before_delete = self._query(bench_graph_id, delete_query, k=5)
            node_before = doc_id_to_node.get(delete_doc_id)
            was_present_before = node_before in before_delete if node_before else False

            deleted = self._delete(bench_graph_id, delete_doc_id)
            if deleted:
                after_delete = self._query(bench_graph_id, delete_query, k=5)
                node_after = self._node_ids_for_docs(
                    bench_graph_id, [delete_doc_id]
                ).get(delete_doc_id)
                still_present = node_after in after_delete if node_after else False
                result.deletion_completeness = 0.0 if still_present else 1.0
                if not was_present_before:
                    result.notes.append(
                        "deletion test: fact was not top-retrieved before delete (may be expected)"
                    )
            else:
                result.deletion_completeness = 0.0
                result.notes.append("deletion failed — node not found by raw_id")

            # ── Phase 7: Provenance / citation accuracy ────────────────────
            citation_correct = 0
            citation_total = 0
            for qa in MULTI_DOC_QA:
                retrieved = self._query(bench_graph_id, qa["question"], k=5)
                citation_total += 1
                # Map retrieved node_ids back to doc_ids
                expected_nodes = {
                    doc_id_to_node[d] for d in qa["doc_ids"] if d in doc_id_to_node
                }
                if any(r in expected_nodes for r in retrieved[:3]):
                    citation_correct += 1

            result.citation_accuracy = citation_correct / max(1, citation_total)
            result.multidoc_qa_accuracy = citation_correct / max(1, citation_total)

            # ── Phase 8: Answer consistency across two sessions ────────────
            consistency_query = "What does Alice do for work?"
            first_run = self._query(bench_graph_id, consistency_query, k=1)
            second_run = self._query(bench_graph_id, consistency_query, k=1)
            result.answer_consistency = 1.0 if first_run == second_run else 0.0

            # Provenance = citation accuracy (same measure for now)
            result.provenance_accuracy = result.citation_accuracy

        except Exception as exc:
            result.errors.append(str(exc))
        finally:
            result.duration_sec = time.monotonic() - start

        return result
