"""FAIM-Native Query Flow (Stage-8).

Orchestrates query execution with:
- Event emission (QUERY_START → QUERY_COMPLETE)
- Candidate recall
- FAIM re-ranking
- Usage tracking (touch_count, last_access)
- Metrics computation

NOT RAG: No chunking, no ST, uses EvidenceBlocks only.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

# Flexible imports
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from core.contracts.types import EventRecord  # noqa: E402
from core.query.query_engine import (  # noqa: E402
    DEFAULT_WEIGHTS,
    STRICT_WEIGHTS,
    build_explain_payload,
    compute_query_hash,
    recall_candidates_brute_force,
    rerank_faim,
)
from encoding.text_vectorizer import vectorize_text  # noqa: E402
from orchestration.ingest_flow import FAIMProfile  # noqa: E402
from store.journal.event_journal import EventJournal  # noqa: E402

# =============================================================================
# Query Result
# =============================================================================


@dataclass
class QueryResult:
    """Result of a query execution."""

    tenant_id: str
    graph_id: str
    graph_version: int
    graph_hash: str
    query_hash: str
    k: int
    results: List[Dict[str, Any]]
    metrics: Dict[str, float]
    profile: FAIMProfile
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response dict."""
        return {
            "tenant_id": self.tenant_id,
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "graph_hash": self.graph_hash,
            "query_hash": self.query_hash,
            "k": self.k,
            "profile": (
                self.profile.name
                if isinstance(self.profile, FAIMProfile)
                else str(self.profile)
            ),
            "results": self.results,
            "metrics": self.metrics,
            "duration_ms": self.duration_ms,
        }


# =============================================================================
# Query Events
# =============================================================================


def emit_query_start(
    journal: EventJournal,
    graph_id: str,
    query_hash: str,
    k: int,
    profile: str,
) -> EventRecord:
    """Emit QUERY_START event."""
    event = EventRecord.create(
        graph_id=graph_id,
        kind="QUERY_START",
        payload={
            "query_hash": query_hash[:16],  # Truncate for SSE
            "k": k,
            "profile": profile,
        },
    )
    return journal.append(event)


def emit_query_reranked(
    journal: EventJournal,
    graph_id: str,
    query_hash: str,
    top_ids: List[str],
) -> EventRecord:
    """Emit QUERY_RERANKED event."""
    event = EventRecord.create(
        graph_id=graph_id,
        kind="QUERY_RERANKED",
        payload={
            "query_hash": query_hash[:16],
            "top_count": len(top_ids),
            "top_ids": top_ids[:5],  # Bounded for SSE
        },
    )
    return journal.append(event)


def emit_query_touch(
    journal: EventJournal,
    graph_id: str,
    node_id: str,
    touch_count: int,
) -> EventRecord:
    """Emit QUERY_TOUCH event for each touched node."""
    event = EventRecord.create(
        graph_id=graph_id,
        kind="QUERY_TOUCH",
        payload={
            "node_id": node_id,
            "touch_count": touch_count,
        },
    )
    return journal.append(event)


def emit_query_complete(
    journal: EventJournal,
    graph_id: str,
    query_hash: str,
    result_count: int,
    duration_ms: float,
    diagnostics_hash: Optional[str] = None,
) -> EventRecord:
    """Emit QUERY_COMPLETE event."""
    event = EventRecord.create(
        graph_id=graph_id,
        kind="QUERY_COMPLETE",
        payload={
            "query_hash": query_hash[:16],
            "result_count": result_count,
            "duration_ms": round(duration_ms, 2),
            "diagnostics_hash": diagnostics_hash[:16] if diagnostics_hash else None,
        },
    )
    return journal.append(event)


# =============================================================================
# Graph Metrics (quick fetch)
# =============================================================================


def get_graph_metrics(session, tenant_id: str, graph_id: str) -> Dict[str, float]:
    """Get graph metrics for query scoring."""
    from sqlalchemy import func
    from store.pg.models_faim import NodeModel

    # Quick stats
    stats = (
        session.query(
            func.count(NodeModel.node_id),
            func.avg(NodeModel.touch_count),
        )
        .filter(
            NodeModel.tenant_id == tenant_id,
            NodeModel.graph_id == graph_id,
        )
        .first()
    )

    node_count = stats[0] or 0
    avg_touch = float(stats[1]) if stats[1] else 1.0

    return {
        "node_count": node_count,
        "avg_touch": avg_touch,
        "CR": 1.0,  # Placeholder
        "R": 0.0,  # Placeholder
        "D_hat": 0.5,
        "H_hat": 0.5,
        "lambda_hat": 0.5,
        "novelty": 0.0,
        "energy": 0.0,
    }


# =============================================================================
# Usage Update
# =============================================================================


def update_usage(
    session,
    tenant_id: str,
    graph_id: str,
    node_ids: List[UUID],
) -> Dict[UUID, int]:
    """Update touch_count and last_access for touched nodes.

    Returns dict of node_id -> new touch_count.
    """
    from store.pg.models_faim import NodeModel

    now = datetime.now(timezone.utc)
    touches = {}

    for node_id in node_ids:
        node = (
            session.query(NodeModel)
            .filter(
                NodeModel.tenant_id == tenant_id,
                NodeModel.graph_id == graph_id,
                NodeModel.node_id == node_id,
            )
            .first()
        )

        if node:
            node.touch_count = (node.touch_count or 0) + 1
            node.last_access = now
            touches[node_id] = node.touch_count

    session.flush()
    return touches


# =============================================================================
# Main Query Flow
# =============================================================================


def run_query(
    session,
    tenant_id: str,
    graph_id: str,
    query_text: str,
    k: int = 10,
    profile: FAIMProfile = FAIMProfile.STRICT,
    return_explain: bool = False,
    index=None,
) -> QueryResult:
    """Execute a FAIM-native query.

    Steps:
    1. Emit QUERY_START
    2. Encode query text → q_vec
    3. Recall candidates
    4. Re-rank with FAIM scoring
    5. Update usage (touch_count)
    6. Emit QUERY_TOUCH for topK
    7. Emit QUERY_COMPLETE

    Args:
        session: Database session.
        tenant_id: Tenant identifier.
        graph_id: Graph identifier.
        query_text: User query.
        k: Number of results to return.
        profile: FAIM profile (STRICT, BALANCED, FAST).
        return_explain: Whether to include explain payload.
        index: Optional FAIMIndex for acceleration.

    Returns:
        QueryResult with ranked nodes and metrics.
    """
    import time

    start_time = time.perf_counter()

    # Initialize journal
    journal = EventJournal(session)

    # Compute query hash
    query_hash = compute_query_hash(query_text, graph_id)
    profile_name = profile.name if isinstance(profile, FAIMProfile) else str(profile)

    # 1. Emit QUERY_START
    emit_query_start(journal, graph_id, query_hash, k, profile_name)

    # 2. Encode query → q_vec (using same vectorizer as ingest)
    q_result = vectorize_text(query_text)
    q_vec = q_result.v_native

    # 3. Get graph metrics
    metrics = get_graph_metrics(session, tenant_id, graph_id)
    graph_avg_touch = metrics.get("avg_touch", 1.0)

    # 4. Recall candidates
    # STRICT mode: always brute-force
    if profile == FAIMProfile.STRICT or index is None:
        candidates = recall_candidates_brute_force(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            q_vec=q_vec,
            n=200,
        )
    else:
        # Use index for acceleration
        from core.query.query_engine import recall_candidates_index

        candidates = recall_candidates_index(
            index=index,
            tenant_id=tenant_id,
            graph_id=graph_id,
            q_vec=q_vec,
            n=200,
        )
        # If index fails, fall back to brute-force
        if not candidates:
            candidates = recall_candidates_brute_force(
                session=session,
                tenant_id=tenant_id,
                graph_id=graph_id,
                q_vec=q_vec,
                n=200,
            )

    candidate_ids = [c[0] for c in candidates]

    # 5. Re-rank with FAIM scoring
    weights = STRICT_WEIGHTS if profile == FAIMProfile.STRICT else DEFAULT_WEIGHTS
    ranked = rerank_faim(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        q_vec=q_vec,
        candidate_ids=candidate_ids,
        graph_avg_touch=graph_avg_touch,
        weights=weights,
        k=k,
    )

    # Emit QUERY_RERANKED
    top_ids = [str(r["node_id"]) for r in ranked]
    emit_query_reranked(journal, graph_id, query_hash, top_ids)

    # 6. Update usage for top results
    result_node_ids = [r["node_id"] for r in ranked]
    touches = update_usage(session, tenant_id, graph_id, result_node_ids)

    # 7. Emit QUERY_TOUCH for each touched node
    for node_id, touch_count in touches.items():
        emit_query_touch(journal, graph_id, str(node_id), touch_count)

    # 8. Build results
    results = []
    for r in ranked:
        result_item = {
            "node_id": str(r["node_id"]),
            "vector_hash": r["vector_hash"],
            "score": r["score"],
            "score_components": r["score_components"],
            "level": r["level"],
            "touch_count": r["touch_count"],
        }

        # Add evidence info
        if r.get("raw_id"):
            result_item["evidence"] = {
                "raw_id": r["raw_id"],
                "block_id": r.get("block_id"),
                "anchor": r.get("anchor"),
            }

        # Add explain if requested
        if return_explain:
            result_item["explain"] = build_explain_payload(
                session, tenant_id, graph_id, r["node_id"]
            )

        results.append(result_item)

    # Get graph version and hash
    from store.pg.repos.graph_version_repo import GraphVersionRepo

    gv_repo = GraphVersionRepo()
    graph_version = gv_repo.get_version(session, graph_id)

    # Compute result
    duration_ms = (time.perf_counter() - start_time) * 1000

    # 9. Emit QUERY_COMPLETE
    emit_query_complete(
        journal, graph_id, query_hash, len(results), duration_ms, query_hash
    )

    return QueryResult(
        tenant_id=tenant_id,
        graph_id=graph_id,
        graph_version=graph_version,
        graph_hash=query_hash,  # Using query_hash as placeholder
        query_hash=query_hash,
        k=k,
        results=results,
        metrics=metrics,
        profile=profile,
        duration_ms=duration_ms,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "QueryResult",
    "run_query",
    "emit_query_start",
    "emit_query_reranked",
    "emit_query_touch",
    "emit_query_complete",
]
