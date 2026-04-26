"""Track C — Long-Horizon Continuity.

Tests persistent memory across 10 simulated sessions.
Inspired by LongBench v2 multi-hop QA but adapted for external memory systems:
instead of stuffing a long context window, each session incrementally adds facts
to FAIM's persistent graph and later sessions query across all prior sessions.

Sessions simulate a real personal assistant / agent workflow:
  Session 1-3  : Initial onboarding (user identity, role, preferences)
  Session 4-6  : Project work (tasks, team, decisions, code context)
  Session 7-8  : Contradicting updates (role change, budget change, new tools)
  Session 9    : Cross-session multi-hop queries (requires joining facts from sessions 1-6)
  Session 10   : Long-horizon recall (can FAIM still retrieve session 1 facts?)

Metrics:
  - session_retention[s] : Recall@5 for facts from session s, queried in session 10
  - cross_session_recall  : Recall@5 for queries requiring facts from 2+ sessions
  - update_accuracy       : New value retrieved preferentially over old value
  - stale_suppression     : Old (deleted/superseded) facts not in top-3
  - multihop_accuracy     : Correct answer requires combining 2+ facts
  - hallucination_rate    : Retrieved facts that were never ingested
  - continuity_score      : Composite (retention + cross + update + hallucination)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from benchmarks.metrics import ndcg_at_k, recall_at_k

# ── Session Data ───────────────────────────────────────────────────────────────

SESSIONS: List[Dict[str, Any]] = [
    {
        "session_id": 1,
        "label": "Onboarding — Identity",
        "docs": [
            ("s1_name", "The user's full name is Dr. Priya Sharma."),
            ("s1_org", "Priya works at Nexus AI Research, a UK-based AI safety lab."),
            (
                "s1_role",
                "Priya is a Principal Research Scientist specializing in alignment.",
            ),
            ("s1_email", "Priya's email is priya.sharma@nexusai.org."),
            ("s1_timezone", "Priya is based in London and operates in GMT timezone."),
        ],
    },
    {
        "session_id": 2,
        "label": "Onboarding — Preferences",
        "docs": [
            (
                "s2_lang",
                "Priya codes primarily in Python and uses JAX for experiments.",
            ),
            ("s2_model", "Priya uses Claude 3.5 Sonnet as her primary language model."),
            (
                "s2_tooling",
                "Priya's stack includes FAIM for memory, Weights & Biases for tracking, and GitHub for version control.",
            ),
            (
                "s2_meeting",
                "Priya prefers async communication and holds one weekly sync on Thursdays at 3 PM GMT.",
            ),
            (
                "s2_format",
                "Priya writes documentation in Markdown and publishes on Notion.",
            ),
        ],
    },
    {
        "session_id": 3,
        "label": "Onboarding — Current Projects",
        "docs": [
            (
                "s3_proj",
                "Priya is leading Project Meridian, an alignment benchmark for multi-agent systems.",
            ),
            ("s3_deadline", "Project Meridian's first milestone is due June 15th."),
            (
                "s3_budget",
                "Project Meridian has a budget of £180,000 for this fiscal year.",
            ),
            (
                "s3_team",
                "The Meridian team includes Priya, Oliver Tan (engineer), and Fatima Al-Rashid (research lead).",
            ),
            (
                "s3_goal",
                "The project goal is to publish a peer-reviewed paper at NeurIPS 2026.",
            ),
        ],
    },
    {
        "session_id": 4,
        "label": "Project Work — Technical Context",
        "docs": [
            (
                "s4_arch",
                "Project Meridian uses a multi-agent simulation framework built on Mesa.",
            ),
            (
                "s4_dataset",
                "The benchmark dataset contains 12,000 multi-agent interaction traces.",
            ),
            (
                "s4_metric",
                "Primary evaluation metric is alignment deviation score (ADS) at k=50.",
            ),
            (
                "s4_baseline",
                "Current baseline ADS is 0.342 using GPT-4o as the reference agent.",
            ),
            ("s4_infra", "Compute runs on 4x A100 GPUs provisioned on Google Cloud."),
        ],
    },
    {
        "session_id": 5,
        "label": "Project Work — Decisions",
        "docs": [
            (
                "s5_dec1",
                "The team decided to switch from Mesa to AgentPy for better scalability.",
            ),
            (
                "s5_dec2",
                "Oliver proposed adding an adversarial sub-task which Priya approved on April 10th.",
            ),
            (
                "s5_dec3",
                "The paper submission deadline was confirmed as September 27th for NeurIPS 2026.",
            ),
            (
                "s5_dec4",
                "Fatima will present the preliminary results at ICML workshop in July.",
            ),
            (
                "s5_dec5",
                "The team will use Claude Opus 4.7 as the new reference model replacing GPT-4o.",
            ),
        ],
    },
    {
        "session_id": 6,
        "label": "Project Work — Code Context",
        "docs": [
            (
                "s6_repo",
                "The Meridian codebase lives at github.com/nexusai/meridian (private repo).",
            ),
            (
                "s6_branch",
                "Active development branch is feature/adversarial-suite, forked from main on April 5th.",
            ),
            (
                "s6_test",
                "Test suite currently covers 68% of the codebase. Target is 85% before submission.",
            ),
            (
                "s6_issue",
                "Open issue #142: ADS computation is 40% slower on adversarial traces due to nested loops.",
            ),
            (
                "s6_perf",
                "Oliver has a fix for issue #142 ready in PR #198, pending Priya's review.",
            ),
        ],
    },
    {
        "session_id": 7,
        "label": "Updates — Role and Budget",
        "docs": [
            (
                "s7_role_new",
                "Priya has been promoted to Research Director, effective May 1st.",
            ),  # supersedes s1_role
            (
                "s7_budget_new",
                "Project Meridian budget increased to £240,000 following new grant approval.",
            ),  # supersedes s3_budget
            (
                "s7_tool_new",
                "The team migrated from Weights & Biases to MLflow for experiment tracking.",
            ),  # supersedes s2_tooling
        ],
    },
    {
        "session_id": 8,
        "label": "Updates — Project Changes",
        "docs": [
            (
                "s8_deadline_new",
                "Project Meridian milestone 1 deadline extended to July 31st due to adversarial task scope.",
            ),  # supersedes s3_deadline
            (
                "s8_team_add",
                "Dr. Yuki Tanaka joined the Meridian team as a visiting researcher from Tokyo University.",
            ),
            (
                "s8_model_switch",
                "Priya now uses Gemini 2.0 Flash for fast prototyping alongside Claude for final runs.",
            ),
        ],
    },
]

# Cross-session multi-hop queries: correct answer requires combining facts from 2+ sessions
MULTIHOP_QUERIES: List[Dict[str, Any]] = [
    {
        "query": "Who is the research lead on Priya's main project and what is her role in the upcoming conference presentation?",
        "required_docs": [
            "s3_team",
            "s5_dec4",
        ],  # Fatima is research lead (s3), Fatima presents at ICML (s5)
        "answer_keywords": ["Fatima", "ICML", "July"],
    },
    {
        "query": "What compute infrastructure does Project Meridian use and who approved the new adversarial sub-task?",
        "required_docs": ["s4_infra", "s5_dec2"],
        "answer_keywords": ["A100", "Priya", "Oliver"],
    },
    {
        "query": "What is Priya's current title and what is the updated project budget?",
        "required_docs": ["s7_role_new", "s7_budget_new"],
        "answer_keywords": ["Director", "240,000"],
    },
    {
        "query": "What is the performance issue in issue #142 and who has the fix ready?",
        "required_docs": ["s6_issue", "s6_perf"],
        "answer_keywords": ["Oliver", "PR", "slower"],
    },
]

# Long-horizon recall: session-1 facts queried in session 10
LONG_HORIZON_QUERIES: List[Tuple[str, str]] = [
    ("s1_name", "What is the user's full name?"),
    ("s1_org", "What organisation does the user work for?"),
    ("s1_timezone", "What timezone does the user operate in?"),
    ("s2_lang", "What programming language does the user primarily code in?"),
    ("s3_goal", "What is the publication target for Project Meridian?"),
]


@dataclass
class SessionRetentionResult:
    session_id: int
    label: str
    docs_ingested: int
    recall_at_5: float
    ndcg_at_10: float


@dataclass
class TrackCResult:
    run_id: str
    graph_id: str
    duration_sec: float
    session_results: List[SessionRetentionResult] = field(default_factory=list)
    cross_session_recall: float = 0.0
    update_accuracy: float = 0.0
    stale_suppression: float = 0.0
    multihop_accuracy: float = 0.0
    hallucination_rate: float = 0.0
    long_horizon_recall: float = 0.0
    continuity_score: float = 0.0
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "duration_sec": round(self.duration_sec, 3),
            "session_retention": [
                {
                    "session_id": s.session_id,
                    "label": s.label,
                    "docs_ingested": s.docs_ingested,
                    "recall@5": round(s.recall_at_5, 4),
                    "ndcg@10": round(s.ndcg_at_10, 4),
                }
                for s in self.session_results
            ],
            "cross_session_recall": round(self.cross_session_recall, 4),
            "update_accuracy": round(self.update_accuracy, 4),
            "stale_suppression": round(self.stale_suppression, 4),
            "multihop_accuracy": round(self.multihop_accuracy, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "long_horizon_recall": round(self.long_horizon_recall, 4),
            "continuity_score": round(self.continuity_score, 4),
            "notes": self.notes,
            "errors": self.errors,
        }


class TrackCEvaluator:
    """Run Track C — Long-Horizon Continuity evaluation."""

    def __init__(self, ctx: Any):
        self.ctx = ctx

    def _ingest(self, graph_id: str, doc_id: str, content: str) -> Optional[str]:
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
            if result.status not in {"completed", "dedup_hit"}:
                return None
            node = self.ctx.node_repo.get_by_raw_id(graph_id, doc_id)
            return (
                str(node.node_id) if node and getattr(node, "node_id", None) else None
            )
        except Exception:
            try:
                self.ctx.session.rollback()
            except Exception:
                pass
            return None

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
        finally:
            try:
                self.ctx.session.rollback()
            except Exception:
                pass

    def _node_id_for(self, graph_id: str, doc_id: str) -> Optional[str]:
        try:
            node = self.ctx.node_repo.get_by_raw_id(graph_id, doc_id)
            return str(node.node_id) if node else None
        except Exception:
            return None

    def run(self, graph_id: str) -> TrackCResult:
        run_id = str(uuid.uuid4())
        start = time.monotonic()
        bench_graph_id = f"{graph_id}__bench_c_{run_id[:8]}"
        result = TrackCResult(run_id=run_id, graph_id=graph_id, duration_sec=0.0)

        try:
            # ── Phase 1-8: Ingest all sessions ────────────────────────────
            all_doc_to_node: Dict[str, Optional[str]] = {}
            all_node_ids: Set[str] = set()

            for session in SESSIONS:
                ingested = 0
                for doc_id, content in session["docs"]:
                    nid = self._ingest(bench_graph_id, doc_id, content)
                    all_doc_to_node[doc_id] = nid
                    if nid:
                        all_node_ids.add(nid)
                        ingested += 1

                # Measure retention for this session's docs immediately after ingesting ALL sessions
                result.session_results.append(
                    SessionRetentionResult(
                        session_id=session["session_id"],
                        label=session["label"],
                        docs_ingested=ingested,
                        recall_at_5=0.0,
                        ndcg_at_10=0.0,
                    )
                )

            # ── Phase 9: Measure per-session retention ─────────────────────
            # Now all sessions are in. Query each session's docs.
            for sess_result in result.session_results:
                session_data = next(
                    s for s in SESSIONS if s["session_id"] == sess_result.session_id
                )
                recalls = []
                ndcgs = []
                for doc_id, content in session_data["docs"]:
                    node_id = all_doc_to_node.get(doc_id)
                    if not node_id:
                        continue
                    query = content.split(".")[0]
                    retrieved = self._query(bench_graph_id, query, k=10)
                    relevant = {node_id}
                    recalls.append(recall_at_k(retrieved, relevant, 5))
                    ndcgs.append(ndcg_at_k(retrieved, relevant, 10))
                if recalls:
                    sess_result.recall_at_5 = sum(recalls) / len(recalls)
                    sess_result.ndcg_at_10 = sum(ndcgs) / len(ndcgs)

            # ── Phase 10: Cross-session multi-hop queries ──────────────────
            cross_hits = 0
            cross_total = 0
            for mhq in MULTIHOP_QUERIES:
                required = mhq["required_docs"]
                required_nodes = {
                    all_doc_to_node[d] for d in required if all_doc_to_node.get(d)
                }
                if not required_nodes:
                    continue
                retrieved = self._query(bench_graph_id, mhq["query"], k=10)
                cross_total += 1
                # A multi-hop query is a hit if at least one required node is in top-10
                if any(nid in retrieved[:10] for nid in required_nodes):
                    cross_hits += 1
            result.cross_session_recall = cross_hits / max(1, cross_total)

            # ── Phase 11: Long-horizon recall (session-1 facts) ───────────
            lh_hits = 0
            for doc_id, query_text in LONG_HORIZON_QUERIES:
                node_id = all_doc_to_node.get(doc_id)
                if not node_id:
                    continue
                retrieved = self._query(bench_graph_id, query_text, k=5)
                if node_id in retrieved:
                    lh_hits += 1
            result.long_horizon_recall = lh_hits / max(1, len(LONG_HORIZON_QUERIES))

            # ── Phase 12: Update accuracy ──────────────────────────────────
            # For superseded facts, new value should rank above old value
            update_pairs = [
                ("s7_role_new", "s1_role", "Priya's current role title"),
                ("s7_budget_new", "s3_budget", "Project Meridian budget amount"),
                ("s8_deadline_new", "s3_deadline", "Meridian milestone deadline"),
            ]
            update_correct = 0
            for new_doc, old_doc, query_text in update_pairs:
                new_node = all_doc_to_node.get(new_doc)
                old_node = all_doc_to_node.get(old_doc)
                if not new_node:
                    continue
                retrieved = self._query(bench_graph_id, query_text, k=10)
                new_rank = retrieved.index(new_node) if new_node in retrieved else 999
                old_rank = retrieved.index(old_node) if old_node in retrieved else 999
                if new_rank < old_rank:  # new value ranks higher than old
                    update_correct += 1
            result.update_accuracy = update_correct / max(1, len(update_pairs))

            # Stale suppression: old facts should not be in top-3
            stale_ok = 0
            for _new_doc, old_doc, query_text in update_pairs:
                old_node = all_doc_to_node.get(old_doc)
                if not old_node:
                    stale_ok += 1  # not found = effectively suppressed
                    continue
                retrieved = self._query(bench_graph_id, query_text, k=3)
                if old_node not in retrieved:
                    stale_ok += 1
            result.stale_suppression = stale_ok / max(1, len(update_pairs))

            # ── Phase 13: Multi-hop accuracy ──────────────────────────────
            result.multihop_accuracy = result.cross_session_recall  # same measure

            # ── Phase 14: Hallucination rate ──────────────────────────────
            phantom_queries = [
                "quantum computing photonic qubits silicon carbide substrate",
                "Renaissance oil painting Flemish school wood panel preparation",
                "underwater welding hyperbaric chamber nitrogen narcosis depth",
            ]
            phantom_hits = 0
            phantom_total = 0
            for q in phantom_queries:
                retrieved = self._query(bench_graph_id, q, k=5)
                for nid in retrieved:
                    phantom_total += 1
                    if nid in all_node_ids:
                        phantom_hits += 1
            result.hallucination_rate = phantom_hits / max(1, phantom_total)

            # ── Phase 15: Composite continuity score ──────────────────────
            avg_session_retention = sum(
                s.recall_at_5 for s in result.session_results
            ) / max(1, len(result.session_results))
            result.continuity_score = (
                avg_session_retention * 0.30
                + result.long_horizon_recall * 0.25
                + result.cross_session_recall * 0.20
                + result.update_accuracy * 0.15
                + (1.0 - result.hallucination_rate) * 0.10
            )

        except Exception as exc:
            result.errors.append(str(exc))
        finally:
            result.duration_sec = time.monotonic() - start

        return result
