"""Query-to-Evidence Reinforcement Learning (Self-Evolve Feedback Loop).

1. On query completion, `record_query_evidence_async` enqueues
   `(query_text -> top cited node_ids)` onto a bounded non-blocking background
   queue backed by Redis (`faim:qrl:{tenant_id}:{graph_id}`), adding ~0 ms to
   FAST query latency and never failing a query if Redis is unavailable.
2. Inside `worker-evolve`, `promote_query_evidence_bridges` drains queued
   feedback events, extracts non-overlapping `(query_concept -> doc_concept)`
   pairs from the cited `NodeRepresentationV2Model.normalized_text`, and
   promotes recurring pairs into `DomainKnowledgeRepo` (`kind="query_reinforcement"`)
   with a `graph_version` bump so subsequent queries benefit immediately.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from lexical.cooccurrence_bridge import _shares_surface_or_stem, extract_concept_terms

logger = logging.getLogger(__name__)

_QRL_MAX_LIST_LEN = 2000
_QRL_TTL_SECONDS = 7 * 24 * 3600
_QRL_QUEUE: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=1024)
_QRL_WORKER_STARTED = False
_QRL_WORKER_LOCK = threading.Lock()


@dataclass(frozen=True)
class QueryReinforcementResult:
    status: str
    events_consumed: int
    bridges_discovered: int
    bridges_persisted: int
    graph_version: Optional[int] = None
    reason: Optional[str] = None


def _qrl_enabled() -> bool:
    if os.getenv("FAIM_BENCHMARK_MODE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return False
    raw = os.getenv("FAIM_QUERY_REINFORCEMENT_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _redis_key(tenant_id: str, graph_id: str) -> str:
    return f"faim:qrl:{tenant_id}:{graph_id}"


def _push_event_to_redis(event: Mapping[str, Any]) -> bool:
    try:
        from cache.redis_client import _get_client

        client = _get_client()
        if client is None:
            return False
        key = _redis_key(str(event["tenant_id"]), str(event["graph_id"]))
        payload = json.dumps(event, separators=(",", ":"))
        pipe = client.pipeline(transaction=False)
        pipe.rpush(key, payload)
        pipe.ltrim(key, -_QRL_MAX_LIST_LEN, -1)
        pipe.expire(key, _QRL_TTL_SECONDS)
        pipe.execute()
        return True
    except Exception as exc:  # nosec B110
        logger.debug("QRL Redis push skipped: %s", exc)
        return False


def _drain_worker_loop() -> None:
    while True:
        event = _QRL_QUEUE.get()
        try:
            _push_event_to_redis(event)
        except Exception:  # nosec B110
            pass
        finally:
            _QRL_QUEUE.task_done()


def _ensure_background_sender() -> None:
    global _QRL_WORKER_STARTED
    if _QRL_WORKER_STARTED:
        return
    with _QRL_WORKER_LOCK:
        if _QRL_WORKER_STARTED:
            return
        thread = threading.Thread(
            target=_drain_worker_loop,
            name="faim-qrl-redis-sender",
            daemon=True,
        )
        thread.start()
        _QRL_WORKER_STARTED = True


def record_query_evidence_async(
    *,
    tenant_id: str,
    graph_id: str,
    query_text: str,
    top_node_ids: Sequence[str],
    reward: float = 1.0,
) -> bool:
    """Non-blocking enqueue of query->evidence feedback for worker-evolve."""
    if not _qrl_enabled():
        return False
    q_clean = " ".join(str(query_text or "").strip().split())
    node_ids = [str(nid) for nid in top_node_ids if nid][:3]
    if not q_clean or not node_ids:
        return False

    _ensure_background_sender()
    event = {
        "tenant_id": str(tenant_id),
        "graph_id": str(graph_id),
        "query_text": q_clean,
        "top_node_ids": node_ids,
        "reward": float(reward),
    }
    try:
        _QRL_QUEUE.put_nowait(event)
        return True
    except queue.Full:
        return False


def _pop_events_from_redis(
    tenant_id: str, graph_id: str, max_events: int = 500
) -> List[Dict[str, Any]]:
    try:
        from cache.redis_client import _get_client

        client = _get_client()
        if client is None:
            return []
        key = _redis_key(tenant_id, graph_id)
        pipe = client.pipeline(transaction=True)
        pipe.lrange(key, 0, max(0, int(max_events) - 1))
        pipe.ltrim(key, int(max_events), -1)
        raw_items, _trimmed = pipe.execute()
        events: List[Dict[str, Any]] = []
        for raw in raw_items or ():
            try:
                text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    events.append(parsed)
            except Exception:
                continue
        return events
    except Exception as exc:  # nosec B110
        logger.debug("QRL Redis pop skipped: %s", exc)
        return []


def promote_query_evidence_bridges(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    events: Optional[Sequence[Mapping[str, Any]]] = None,
    min_reinforcement_count: int = 2,
    max_bridges_per_term: int = 4,
    max_total_bridges: int = 250,
) -> QueryReinforcementResult:
    """Consolidate recurring query->evidence pairs into DomainKnowledgeRepo."""
    if session is None:
        return QueryReinforcementResult(
            status="skipped",
            events_consumed=0,
            bridges_discovered=0,
            bridges_persisted=0,
            reason="no_session",
        )

    batch = list(events) if events is not None else _pop_events_from_redis(tenant_id, graph_id)
    if not batch:
        return QueryReinforcementResult(
            status="skipped",
            events_consumed=0,
            bridges_discovered=0,
            bridges_persisted=0,
            reason="no_feedback_events",
        )

    from uuid import UUID
    from store.pg.models_faim import NodeRepresentationV2Model
    from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo

    needed_ids = set()
    for ev in batch:
        for raw_id in ev.get("top_node_ids") or ():
            try:
                needed_ids.add(UUID(str(raw_id)))
            except Exception:
                continue

    if not needed_ids:
        return QueryReinforcementResult(
            status="skipped",
            events_consumed=len(batch),
            bridges_discovered=0,
            bridges_persisted=0,
            reason="no_valid_node_ids",
        )

    repr_rows = (
        session.query(
            NodeRepresentationV2Model.node_id,
            NodeRepresentationV2Model.normalized_text,
        )
        .filter(
            NodeRepresentationV2Model.tenant_id == tenant_id,
            NodeRepresentationV2Model.graph_id == graph_id,
            NodeRepresentationV2Model.node_id.in_(list(needed_ids)),
        )
        .all()
    )
    node_texts: Dict[str, str] = {
        str(nid): str(text or "") for nid, text in repr_rows if str(text or "").strip()
    }

    pair_weights: Counter[Tuple[str, str]] = Counter()
    pair_counts: Counter[Tuple[str, str]] = Counter()
    pair_nodes: Dict[Tuple[str, str], set] = defaultdict(set)

    for ev in batch:
        q_terms = extract_concept_terms(str(ev.get("query_text") or ""))
        if not q_terms:
            continue
        reward = max(0.1, float(ev.get("reward", 1.0) or 1.0))
        top_ids = [str(x) for x in (ev.get("top_node_ids") or ())[:3]]
        for rank_idx, nid in enumerate(top_ids):
            doc_text = node_texts.get(nid)
            if not doc_text:
                continue
            d_terms = extract_concept_terms(doc_text)[:12]
            rank_decay = 1.0 / (1.0 + 0.5 * rank_idx)
            step_weight = reward * rank_decay
            for qt in q_terms:
                for dt in d_terms:
                    if _shares_surface_or_stem(qt, dt):
                        continue
                    pair = (qt, dt)
                    pair_counts[pair] += 1
                    pair_weights[pair] += step_weight
                    pair_nodes[pair].add(nid)

    by_source: Dict[str, List[Tuple[float, str, int, List[str]]]] = defaultdict(list)
    for (qt, dt), count in pair_counts.items():
        if count < int(min_reinforcement_count):
            continue
        weight_sum = float(pair_weights[(qt, dt)])
        score = min(0.95, max(0.55, round(0.50 + 0.12 * min(3.75, weight_sum), 4)))
        nodes_list = sorted(pair_nodes[(qt, dt)])[:5]
        by_source[qt].append((score, dt, count, nodes_list))

    rows: List[Dict[str, Any]] = []
    for qt in sorted(by_source):
        ranked = sorted(
            by_source[qt], key=lambda item: (-item[0], -item[2], item[1])
        )[: max(1, int(max_bridges_per_term))]
        bundle = [dt for _sc, dt, _cnt, _nids in ranked]
        for score, dt, count, nodes_list in ranked:
            rows.append(
                {
                    "surface_form": qt,
                    "canonical_form": dt,
                    "kind": "query_reinforcement",
                    "domain_pack": "query_reinforcement_v1",
                    "support_count": count,
                    "score": score,
                    "meta": {
                        "source": "query_reinforcement_v1",
                        "node_ids": nodes_list,
                        "bundle_members": bundle,
                    },
                }
            )

    if not rows:
        return QueryReinforcementResult(
            status="skipped",
            events_consumed=len(batch),
            bridges_discovered=0,
            bridges_persisted=0,
            reason="below_min_reinforcement_count",
        )

    rows.sort(
        key=lambda r: (
            -float(r["score"]),
            -int(r["support_count"]),
            str(r["surface_form"]),
            str(r["canonical_form"]),
        )
    )
    rows = rows[: max(1, int(max_total_bridges))]

    domain_repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
    persisted = domain_repo.merge_lexicon(graph_id, rows)
    new_version: Optional[int] = None
    if persisted > 0:
        gv_repo = GraphVersionRepo(tenant_id=tenant_id)
        new_version = gv_repo.bump(
            session,
            graph_id=graph_id,
            reason=f"query_reinforcement: {persisted} bridges",
        )

    return QueryReinforcementResult(
        status="completed",
        events_consumed=len(batch),
        bridges_discovered=len(rows),
        bridges_persisted=persisted,
        graph_version=new_version,
    )


__all__ = [
    "QueryReinforcementResult",
    "promote_query_evidence_bridges",
    "record_query_evidence_async",
]
