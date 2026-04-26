"""Track F — Real-World Tasks (multi-doc QA, writing continuity, code context).

Tests:
  - Multi-document question answering
  - Writing continuity with user preference updates
  - Personal assistant continuity
  - Code project context retention
  - Citation accuracy
  - Stale fact suppression

Metrics:
  - multi_doc_qa_accuracy
  - writing_continuity_score
  - personal_assistant_continuity
  - code_project_context_retention
  - citation_accuracy
  - stale_fact_suppression
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from benchmarks.dataset_manager import BeirDataset


@dataclass
class TrackFResult:
    run_id: str
    graph_id: str
    duration_sec: float
    multi_doc_qa_accuracy: float = 0.0
    writing_continuity_score: float = 0.0
    personal_assistant_continuity: float = 0.0
    code_project_context_retention: float = 0.0
    citation_accuracy: float = 0.0
    stale_fact_suppression: float = 0.0
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "duration_sec": round(self.duration_sec, 3),
            "multi_doc_qa_accuracy": round(self.multi_doc_qa_accuracy, 4),
            "writing_continuity_score": round(self.writing_continuity_score, 4),
            "personal_assistant_continuity": round(
                self.personal_assistant_continuity, 4
            ),
            "code_project_context_retention": round(
                self.code_project_context_retention, 4
            ),
            "citation_accuracy": round(self.citation_accuracy, 4),
            "stale_fact_suppression": round(self.stale_fact_suppression, 4),
            "notes": self.notes,
            "errors": self.errors,
        }


class TrackFEvaluator:
    """Evaluates real-world task continuity: multi-doc QA, writing, assistant preferences, code context."""

    def __init__(self, ctx: Any):
        """
        Args:
            ctx: PublicationRunnerContext with tenant_id, session, cache
        """
        self.ctx = ctx

    def build_dataset(self) -> BeirDataset:
        """Build synthetic real-world task test dataset."""
        corpus = {
            "doc_qna_1": {
                "title": "Project update",
                "text": "The release date moved to May 20 and the client requested a short summary with citations.",
            },
            "doc_qna_2": {
                "title": "Source notes",
                "text": "The summary must cite the architecture note and the security note together.",
            },
            "doc_personal_1": {
                "title": "Assistant preference",
                "text": "The user prefers concise bullet-free answers and wants follow-up corrections preserved.",
            },
            "doc_personal_2": {
                "title": "Preference correction",
                "text": "The user later changed the preference to allow short bullet lists only when requested.",
            },
            "doc_code_1": {
                "title": "Code project context",
                "text": "The active branch is feature/memory-eval and the failing test is test_publication_suite.",
            },
            "doc_code_2": {
                "title": "Code project update",
                "text": "The bug was fixed by refreshing the benchmark cache after each run.",
            },
            "doc_write_1": {
                "title": "Writing brief",
                "text": "Write a grounded status note that mentions the release date, the branch name, and the user preference correction.",
            },
            "doc_write_2": {
                "title": "Writing constraint",
                "text": "Do not invent facts that are not in the cited documents.",
            },
        }
        queries = {
            "q_multi_doc": "Which documents should be cited for the project update and summary request?",
            "q_write": "What facts must appear in the grounded status note?",
            "q_personal": "What writing style does the user want after the correction?",
            "q_code": "What is the active branch and what fixed the failing test?",
            "q_citation": "Which documents support the citation requirement?",
            "q_stale": "Should the old instruction still be followed?",
        }
        qrels = {
            "q_multi_doc": {"doc_qna_1", "doc_qna_2"},
            "q_write": {"doc_write_1", "doc_write_2"},
            "q_personal": {"doc_personal_1", "doc_personal_2"},
            "q_code": {"doc_code_1", "doc_code_2"},
            "q_citation": {"doc_qna_2", "doc_write_2"},
            "q_stale": {"doc_personal_2"},
        }
        return BeirDataset("track_f_real_world_tasks", corpus, queries, qrels)
