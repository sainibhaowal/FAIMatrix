"""Track E — Agent & API Workflow (API key continuity, multi-agent isolation).

Tests:
  - API key lifecycle (create, list, revoke operations)
  - Task completion across workflow steps
  - Tool-call memory recall
  - Multi-agent isolation (no cross-namespace leakage)

Metrics:
  - api_key_access_memory_accuracy
  - task_completion_rate
  - tool_call_memory_recall_accuracy
  - multi_agent_isolation_correctness
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from benchmarks.dataset_manager import BeirDataset


@dataclass
class TrackEResult:
    run_id: str
    graph_id: str
    duration_sec: float
    api_key_access_memory_accuracy: float = 0.0
    task_completion_rate: float = 0.0
    tool_call_memory_recall_accuracy: float = 0.0
    multi_agent_isolation_correctness: float = 0.0
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "duration_sec": round(self.duration_sec, 3),
            "api_key_access_memory_accuracy": round(
                self.api_key_access_memory_accuracy, 4
            ),
            "task_completion_rate": round(self.task_completion_rate, 4),
            "tool_call_memory_recall_accuracy": round(
                self.tool_call_memory_recall_accuracy, 4
            ),
            "multi_agent_isolation_correctness": round(
                self.multi_agent_isolation_correctness, 4
            ),
            "notes": self.notes,
            "errors": self.errors,
        }


class TrackEEvaluator:
    """Evaluates agent workflows, API key continuity, and multi-agent isolation."""

    def __init__(self, ctx: Any):
        """
        Args:
            ctx: PublicationRunnerContext with tenant_id, session, cache
        """
        self.ctx = ctx

    def build_dataset(self) -> BeirDataset:
        """Build synthetic agent workflow test dataset."""
        corpus = {
            "api_key_created": {
                "title": "API key created",
                "text": "A key with prefix faim_pub_7f3c was created and must still work on the next call.",
            },
            "api_key_revoked": {
                "title": "API key revoked",
                "text": "The same key was revoked only after the follow-up verification call.",
            },
            "task_step_1": {
                "title": "Task step 1",
                "text": "Step 1: confirm tenant identity and remember the tenant_id across the workflow.",
            },
            "task_step_2": {
                "title": "Task step 2",
                "text": "Step 2: capture the updated preference that the user now wants concise answers.",
            },
            "task_step_3": {
                "title": "Task step 3",
                "text": "Step 3: remember the correction that the assistant must not reuse the stale draft.",
            },
            "task_step_4": {
                "title": "Task step 4",
                "text": "Step 4: finish the checklist only after all prior steps are acknowledged.",
            },
            "tool_call_1": {
                "title": "Tool call one",
                "text": "The first tool call returned a graph_id, a request_id, and a memory checkpoint token.",
            },
            "tool_call_2": {
                "title": "Tool call two",
                "text": "The second tool call reused the checkpoint token and preserved the earlier graph_id.",
            },
            "agent_alpha": {
                "title": "Agent alpha",
                "text": "Agent alpha owns the alpha memory namespace and must not see beta-private notes.",
            },
            "agent_beta": {
                "title": "Agent beta",
                "text": "Agent beta owns the beta namespace and must not read alpha-private notes.",
            },
        }
        queries = {
            "q_api_key": "What key prefix must be remembered on the next call?",
            "q_api_key_followup": "Was the same key still valid on the follow-up call?",
            "q_step_completion": "Which step completes the workflow after the prior acknowledgements?",
            "q_tool_recall": "What token did the second tool call reuse?",
            "q_agent_alpha": "Which agent owns the alpha namespace?",
            "q_agent_beta": "Which agent must not see alpha-private notes?",
        }
        qrels = {
            "q_api_key": {"api_key_created"},
            "q_api_key_followup": {"api_key_revoked"},
            "q_step_completion": {"task_step_4"},
            "q_tool_recall": {"tool_call_2"},
            "q_agent_alpha": {"agent_alpha"},
            "q_agent_beta": {"agent_beta"},
        }
        return BeirDataset("track_e_agent_workflow", corpus, queries, qrels)

    def auth_key_lifecycle_probe(self) -> Dict[str, Any]:
        """Test API key creation, listing, and revocation."""
        from store.pg.repos.auth_repo import AuthRepo

        repo = AuthRepo(self.ctx.session)
        record, plaintext = repo.create_tenant_key(
            self.ctx.tenant_id, scopes=["memory.read"]
        )
        listed = repo.list_tenant_keys(self.ctx.tenant_id, include_revoked=False)
        repo.revoke_tenant_key(
            self.ctx.tenant_id, record.key_id, reason="publication_suite_probe"
        )
        listed_after = repo.list_tenant_keys(self.ctx.tenant_id, include_revoked=False)
        try:
            self.ctx.session.commit()
        except Exception:
            self.ctx.session.rollback()
            raise
        return {
            "created_key_id": record.key_id,
            "plaintext_prefix": plaintext[:8],
            "listed_before_revoke": any(
                item.key_id == record.key_id for item in listed
            ),
            "listed_after_revoke": any(
                item.key_id == record.key_id for item in listed_after
            ),
            "passed": any(item.key_id == record.key_id for item in listed)
            and all(item.key_id != record.key_id for item in listed_after),
        }

    def multi_agent_isolation_probe(self, graph_id: str) -> Dict[str, Any]:
        """Test that agents cannot cross namespaces."""
        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest
        from orchestration.query_flow import FAIMProfile as QueryProfile
        from orchestration.query_flow import run_query

        alpha_graph = f"{graph_id}__alpha__{uuid.uuid4().hex[:6]}"
        beta_graph = f"{graph_id}__beta__{uuid.uuid4().hex[:6]}"
        run_ingest(
            graph_id=alpha_graph,
            raw_id="alpha_secret",
            filename="alpha_secret.txt",
            file_bytes=b"Agent alpha owns the alpha private note and the codeword violet.",
            tenant_id=self.ctx.tenant_id,
            session=self.ctx.session,
            profile=FAIMProfile.STRICT,
            persist_mode=PersistMode.STRICT,
        )
        run_ingest(
            graph_id=beta_graph,
            raw_id="beta_secret",
            filename="beta_secret.txt",
            file_bytes=b"Agent beta owns the beta private note and the codeword amber.",
            tenant_id=self.ctx.tenant_id,
            session=self.ctx.session,
            profile=FAIMProfile.STRICT,
            persist_mode=PersistMode.STRICT,
        )
        try:
            alpha_query = run_query(
                session=self.ctx.session,
                tenant_id=self.ctx.tenant_id,
                graph_id=alpha_graph,
                query_text="What is alpha's codeword?",
                k=5,
                profile=QueryProfile.STRICT,
                return_explain=False,
                index=None,
                cache=self.ctx.cache,
            )
            beta_query = run_query(
                session=self.ctx.session,
                tenant_id=self.ctx.tenant_id,
                graph_id=beta_graph,
                query_text="What is beta's codeword?",
                k=5,
                profile=QueryProfile.STRICT,
                return_explain=False,
                index=None,
                cache=self.ctx.cache,
            )
            cross_alpha = run_query(
                session=self.ctx.session,
                tenant_id=self.ctx.tenant_id,
                graph_id=alpha_graph,
                query_text="What is beta's codeword?",
                k=5,
                profile=QueryProfile.STRICT,
                return_explain=False,
                index=None,
                cache=self.ctx.cache,
            )
        finally:
            try:
                self.ctx.session.rollback()
            except Exception:
                pass

        alpha_ids = {str(item["node_id"]) for item in alpha_query.results}
        beta_ids = {str(item["node_id"]) for item in beta_query.results}
        cross_alpha_ids = {str(item["node_id"]) for item in cross_alpha.results}

        alpha_node = None
        beta_node = None
        try:
            alpha_row = self.ctx.node_repo.get_by_raw_id(alpha_graph, "alpha_secret")
            if alpha_row and getattr(alpha_row, "node_id", None):
                alpha_node = str(alpha_row.node_id)
        except Exception:
            pass
        try:
            beta_row = self.ctx.node_repo.get_by_raw_id(beta_graph, "beta_secret")
            if beta_row and getattr(beta_row, "node_id", None):
                beta_node = str(beta_row.node_id)
        except Exception:
            pass
        passed = bool(
            alpha_node in alpha_ids
            and beta_node in beta_ids
            and beta_node not in cross_alpha_ids
        )

        return {
            "alpha_node": alpha_node,
            "beta_node": beta_node,
            "alpha_query_hit": alpha_node in alpha_ids if alpha_node else False,
            "beta_query_hit": beta_node in beta_ids if beta_node else False,
            "cross_graph_leak": beta_node in cross_alpha_ids if beta_node else False,
            "passed": passed,
        }
