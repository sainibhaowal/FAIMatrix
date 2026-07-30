"""Graph-scoped domain intelligence for FAIM.

This module turns the existing autonomous domain-memory layer into a
dedicated read surface for product and operator inspection.
"""

from __future__ import annotations

import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session

from store.pg.models_faim import (
    EdgeModel,
    GraphDomainLexiconModel,
    GraphKBSourceModel,
    NodeModel,
)
from store.pg.repos.graph_version_repo import GraphVersionRepo


def _jobs_enabled() -> bool:
    return os.getenv("FAIM_ENABLE_JOBS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _domain_autonomy_enabled() -> bool:
    raw = os.getenv("FAIM_DOMAIN_AUTONOMY_ENABLED", "").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _node_label(node: NodeModel) -> str:
    anchor = dict(node.anchor_json or {})
    for key in ("title", "label", "text", "preview", "summary", "content"):
        value = anchor.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:64]
    for key in ("block_id", "raw_id", "cognitive_type", "kind"):
        value = getattr(node, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()[:64]
    return str(node.node_id)


def _iso_or_none(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _coerce_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _maturity_score(
    *,
    lexicon_total: int,
    source_total: int,
    pack_total: int,
    linked_total: int,
    kind_total: int,
) -> int:
    # Bounded heuristic score for product visibility, not a scientific metric.
    score = 0.0
    score += min(40.0, math.log1p(max(lexicon_total, 0)) * 8.0)
    score += min(18.0, math.log1p(max(source_total, 0)) * 7.0)
    score += min(14.0, float(max(pack_total, 0)) * 2.5)
    score += min(18.0, math.log1p(max(linked_total, 0)) * 6.0)
    score += min(10.0, float(max(kind_total, 0)) * 1.5)
    return int(max(0.0, min(100.0, round(score))))


def build_domain_overview(
    *,
    session: Session,
    tenant_id: str,
    graph_id: str,
    limit: int = 12,
) -> Dict[str, Any]:
    """Return graph-scoped domain-learning overview data."""
    graph_version = GraphVersionRepo(session=session, tenant_id=tenant_id).get_version(
        session, graph_id
    )

    lexicon_query = session.query(GraphDomainLexiconModel).filter(
        and_(
            GraphDomainLexiconModel.tenant_id == tenant_id,
            GraphDomainLexiconModel.graph_id == graph_id,
        )
    )
    source_query = session.query(GraphKBSourceModel).filter(
        and_(
            GraphKBSourceModel.tenant_id == tenant_id,
            GraphKBSourceModel.graph_id == graph_id,
        )
    )

    lexicon_total = int(lexicon_query.count())
    source_total = int(source_query.count())

    top_rows = (
        lexicon_query.order_by(
            desc(GraphDomainLexiconModel.score),
            desc(GraphDomainLexiconModel.support_count),
            asc(GraphDomainLexiconModel.surface_form),
            asc(GraphDomainLexiconModel.canonical_form),
        )
        .limit(limit)
        .all()
    )
    source_rows = (
        source_query.order_by(
            desc(GraphKBSourceModel.updated_at),
            asc(GraphKBSourceModel.source_id),
        )
        .limit(limit)
        .all()
    )
    kind_rows = (
        session.query(
            GraphDomainLexiconModel.kind,
            func.count(GraphDomainLexiconModel.surface_form),
        )
        .filter(
            and_(
                GraphDomainLexiconModel.tenant_id == tenant_id,
                GraphDomainLexiconModel.graph_id == graph_id,
            )
        )
        .group_by(GraphDomainLexiconModel.kind)
        .all()
    )
    pack_rows = (
        session.query(
            GraphDomainLexiconModel.domain_pack,
            func.count(GraphDomainLexiconModel.surface_form),
            func.coalesce(func.sum(GraphDomainLexiconModel.support_count), 0),
            func.coalesce(func.avg(GraphDomainLexiconModel.score), 0.0),
        )
        .filter(
            and_(
                GraphDomainLexiconModel.tenant_id == tenant_id,
                GraphDomainLexiconModel.graph_id == graph_id,
                GraphDomainLexiconModel.domain_pack.isnot(None),
            )
        )
        .group_by(GraphDomainLexiconModel.domain_pack)
        .order_by(
            desc(func.count(GraphDomainLexiconModel.surface_form)),
            desc(func.coalesce(func.avg(GraphDomainLexiconModel.score), 0.0)),
            asc(GraphDomainLexiconModel.domain_pack),
        )
        .all()
    )
    source_kind_rows = (
        session.query(
            GraphKBSourceModel.source_kind,
            func.count(GraphKBSourceModel.source_id),
        )
        .filter(
            and_(
                GraphKBSourceModel.tenant_id == tenant_id,
                GraphKBSourceModel.graph_id == graph_id,
            )
        )
        .group_by(GraphKBSourceModel.source_kind)
        .all()
    )

    linked_total = 0
    last_updated_at: Optional[datetime] = None
    detected_packs: List[str] = []
    top_terms: List[Dict[str, Any]] = []
    for row in top_rows:
        meta = dict(row.meta or {})
        has_node = bool(meta.get("node_id"))
        if has_node:
            linked_total += 1
        if row.domain_pack and row.domain_pack not in detected_packs:
            detected_packs.append(str(row.domain_pack))
        if last_updated_at is None or (
            row.updated_at is not None and row.updated_at > last_updated_at
        ):
            last_updated_at = row.updated_at
        top_terms.append(
            {
                "surface_form": row.surface_form,
                "canonical_form": row.canonical_form,
                "kind": row.kind,
                "domain_pack": row.domain_pack,
                "support_count": int(row.support_count or 0),
                "score": float(row.score or 0.0),
                "has_node": has_node,
                "node_id": str(meta.get("node_id")) if meta.get("node_id") else None,
                "meta": meta,
                "updated_at": _iso_or_none(row.updated_at),
            }
        )

    top_sources: List[Dict[str, Any]] = []
    for row in source_rows:
        if last_updated_at is None or (
            row.updated_at is not None and row.updated_at > last_updated_at
        ):
            last_updated_at = row.updated_at
        top_sources.append(
            {
                "source_id": row.source_id,
                "source_kind": row.source_kind,
                "source_hash": row.source_hash,
                "meta": dict(row.meta or {}),
                "updated_at": _iso_or_none(row.updated_at),
            }
        )

    kind_breakdown = [
        {"kind": str(kind), "count": int(count)}
        for kind, count in sorted(kind_rows, key=lambda item: (-int(item[1]), str(item[0])))
    ]
    pack_strengths = [
        {
            "domain_pack": str(pack),
            "term_count": int(term_count),
            "support_total": int(support_total or 0),
            "avg_score": float(avg_score or 0.0),
        }
        for pack, term_count, support_total, avg_score in pack_rows
        if pack
    ]
    source_kinds = [
        {"source_kind": str(kind), "count": int(count)}
        for kind, count in sorted(
            source_kind_rows, key=lambda item: (-int(item[1]), str(item[0]))
        )
    ]

    maturity_score = _maturity_score(
        lexicon_total=lexicon_total,
        source_total=source_total,
        pack_total=len(pack_strengths),
        linked_total=linked_total,
        kind_total=len(kind_breakdown),
    )

    return {
        "graph_id": graph_id,
        "graph_version": int(graph_version),
        "jobs_enabled": _jobs_enabled(),
        "domain_autonomy_enabled": _domain_autonomy_enabled(),
        "lexicon_total": lexicon_total,
        "source_total": source_total,
        "linked_total": linked_total,
        "maturity_score": maturity_score,
        "detected_packs": detected_packs or ["general"],
        "kind_breakdown": kind_breakdown,
        "pack_strengths": pack_strengths,
        "source_kinds": source_kinds,
        "top_terms": top_terms,
        "top_sources": top_sources,
        "last_updated_at": _iso_or_none(last_updated_at),
    }


def list_domain_terms(
    *,
    session: Session,
    tenant_id: str,
    graph_id: str,
    limit: int = 50,
    offset: int = 0,
    q: Optional[str] = None,
    kind: Optional[str] = None,
    domain_pack: Optional[str] = None,
) -> Dict[str, Any]:
    """Return filtered domain terms for the graph."""
    query = session.query(GraphDomainLexiconModel).filter(
        and_(
            GraphDomainLexiconModel.tenant_id == tenant_id,
            GraphDomainLexiconModel.graph_id == graph_id,
        )
    )

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                GraphDomainLexiconModel.surface_form.ilike(pattern),
                GraphDomainLexiconModel.canonical_form.ilike(pattern),
            )
        )
    if kind and kind.strip():
        query = query.filter(GraphDomainLexiconModel.kind == kind.strip())
    if domain_pack and domain_pack.strip():
        query = query.filter(GraphDomainLexiconModel.domain_pack == domain_pack.strip())

    total = int(query.count())
    rows = (
        query.order_by(
            desc(GraphDomainLexiconModel.score),
            desc(GraphDomainLexiconModel.support_count),
            asc(GraphDomainLexiconModel.surface_form),
            asc(GraphDomainLexiconModel.canonical_form),
        )
        .limit(limit)
        .offset(offset)
        .all()
    )

    items = []
    for row in rows:
        meta = dict(row.meta or {})
        items.append(
            {
                "surface_form": row.surface_form,
                "canonical_form": row.canonical_form,
                "kind": row.kind,
                "domain_pack": row.domain_pack,
                "support_count": int(row.support_count or 0),
                "score": float(row.score or 0.0),
                "has_node": bool(meta.get("node_id")),
                "node_id": str(meta.get("node_id")) if meta.get("node_id") else None,
                "meta": meta,
                "updated_at": _iso_or_none(row.updated_at),
            }
        )

    return {
        "graph_id": graph_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


def build_domain_graph(
    *,
    session: Session,
    tenant_id: str,
    graph_id: str,
    limit: int = 24,
) -> Dict[str, Any]:
    """Return a bounded graph view for learned domain memory."""
    rows = (
        session.query(GraphDomainLexiconModel)
        .filter(
            and_(
                GraphDomainLexiconModel.tenant_id == tenant_id,
                GraphDomainLexiconModel.graph_id == graph_id,
            )
        )
        .order_by(
            desc(GraphDomainLexiconModel.score),
            desc(GraphDomainLexiconModel.support_count),
            asc(GraphDomainLexiconModel.surface_form),
            asc(GraphDomainLexiconModel.canonical_form),
        )
        .limit(limit)
        .all()
    )

    if not rows:
        graph_version = GraphVersionRepo(
            session=session, tenant_id=tenant_id
        ).get_version(session, graph_id)
        return {
            "graph_id": graph_id,
            "graph_version": int(graph_version),
            "nodes": [],
            "edges": [],
            "terms_sampled": 0,
            "packs_sampled": 0,
            "linked_nodes_sampled": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    graph_version = GraphVersionRepo(session=session, tenant_id=tenant_id).get_version(
        session, graph_id
    )

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_node_ids = set()
    canonical_surfaces: Dict[str, set[str]] = defaultdict(set)
    linked_refs: Dict[UUID, Counter[str]] = defaultdict(Counter)

    for row in rows:
        canonical_surfaces[row.canonical_form].add(row.surface_form)
        node_id = _coerce_uuid(dict(row.meta or {}).get("node_id"))
        if node_id is not None:
            linked_refs[node_id][row.surface_form] += 1

    def add_node(payload: Dict[str, Any]) -> None:
        node_id = str(payload["id"])
        if node_id in seen_node_ids:
            return
        seen_node_ids.add(node_id)
        nodes.append(payload)

    pack_ids: Dict[str, str] = {}
    canonical_ids: Dict[str, str] = {}

    for row in rows:
        meta = dict(row.meta or {})
        pack = str(row.domain_pack or "general")
        pack_id = pack_ids.setdefault(pack, f"pack:{pack}")
        add_node(
            {
                "id": pack_id,
                "label": pack.replace("_", " "),
                "type": "pack",
                "pack": pack,
                "kind": "domain_pack",
            }
        )

        bundle_key = str(meta.get("bundle_key") or "").strip()
        if row.kind == "concept_bundle" and bundle_key:
            bundle_id = f"bundle:{bundle_key}"
            add_node(
                {
                    "id": bundle_id,
                    "label": row.surface_form,
                    "type": "bundle",
                    "pack": pack,
                    "kind": row.kind,
                    "score": float(row.score or 0.0),
                    "support_count": int(row.support_count or 0),
                    "canonical_form": row.canonical_form,
                }
            )
            edges.append(
                {
                    "id": f"{pack_id}->{bundle_id}",
                    "source": pack_id,
                    "target": bundle_id,
                    "kind": "domain_pack",
                    "weight": max(0.3, min(1.0, float(row.score or 0.0))),
                }
            )
            for member in list(meta.get("bundle_members") or [])[:8]:
                member_surface = str(member or "").strip()
                if not member_surface:
                    continue
                term_member_id = f"term:{member_surface}:{row.kind}:{row.canonical_form}"
                add_node(
                    {
                        "id": term_member_id,
                        "label": member_surface,
                        "type": "term",
                        "pack": pack,
                        "kind": "bundle_member",
                        "score": float(row.score or 0.0),
                        "support_count": int(row.support_count or 0),
                        "canonical_form": row.canonical_form,
                    }
                )
                edges.append(
                    {
                        "id": f"{bundle_id}->{term_member_id}",
                        "source": bundle_id,
                        "target": term_member_id,
                        "kind": "bundle_member",
                        "weight": max(0.3, min(1.0, float(row.score or 0.0))),
                    }
                )

        canonical_needed = (
            row.canonical_form != row.surface_form
            or len(canonical_surfaces[row.canonical_form]) > 1
        )
        canonical_id: Optional[str] = None
        if canonical_needed:
            canonical_id = canonical_ids.setdefault(
                row.canonical_form, f"canonical:{row.canonical_form}"
            )
            add_node(
                {
                    "id": canonical_id,
                    "label": row.canonical_form,
                    "type": "canonical",
                    "pack": pack,
                    "kind": row.kind,
                }
            )
            edges.append(
                {
                    "id": f"{pack_id}->{canonical_id}",
                    "source": pack_id,
                    "target": canonical_id,
                    "kind": "domain_pack",
                    "weight": 0.55,
                }
            )

        term_id = f"term:{row.surface_form}:{row.kind}:{row.canonical_form}"
        add_node(
            {
                "id": term_id,
                "label": row.surface_form,
                "type": "term",
                "pack": pack,
                "kind": row.kind,
                "score": float(row.score or 0.0),
                "support_count": int(row.support_count or 0),
                "canonical_form": row.canonical_form,
            }
        )
        edges.append(
            {
                "id": f"{pack_id}->{term_id}",
                "source": pack_id,
                "target": term_id,
                "kind": "pack_term",
                "weight": max(0.2, min(1.0, float(row.score or 0.0))),
            }
        )
        if canonical_id:
            edges.append(
                {
                    "id": f"{term_id}->{canonical_id}",
                    "source": term_id,
                    "target": canonical_id,
                    "kind": "canonicalizes_to",
                    "weight": 0.65,
                }
            )

        linked = _coerce_uuid(meta.get("node_id"))
        if linked is not None:
            linked_id = f"graph:{linked}"
            add_node(
                {
                    "id": linked_id,
                    "label": str(linked),
                    "type": "graph",
                    "pack": pack,
                    "kind": "linked_graph_node",
                }
            )
            edges.append(
                {
                    "id": f"{term_id}->{linked_id}",
                    "source": term_id,
                    "target": linked_id,
                    "kind": "graph_link",
                    "weight": 0.75,
                }
            )

    linked_models = {}
    if linked_refs:
        linked_models = {
            row.node_id: row
            for row in session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == tenant_id,
                    NodeModel.graph_id == graph_id,
                    NodeModel.node_id.in_(list(linked_refs.keys())),
                )
            )
            .all()
        }
        for linked_id, node in linked_models.items():
            node_key = f"graph:{linked_id}"
            if node_key not in seen_node_ids:
                continue
            for payload in nodes:
                if payload["id"] == node_key:
                    payload["label"] = _node_label(node)
                    payload["kind"] = node.kind
                    payload["cognitive_type"] = node.cognitive_type
                    payload["cluster_id"] = node.cluster_id
                    break

        real_edges = (
            session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.tenant_id == tenant_id,
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.src_node_id.in_(list(linked_refs.keys())),
                    EdgeModel.dst_node_id.in_(list(linked_refs.keys())),
                )
            )
            .limit(max(16, len(linked_refs) * 2))
            .all()
        )
        for edge in real_edges:
            src = f"graph:{edge.src_node_id}"
            dst = f"graph:{edge.dst_node_id}"
            if src in seen_node_ids and dst in seen_node_ids:
                edges.append(
                    {
                        "id": f"edge:{edge.edge_id}",
                        "source": src,
                        "target": dst,
                        "kind": edge.kind,
                        "weight": float(edge.weight or 0) / 1e9 if edge.weight else 0.0,
                    }
                )

    return {
        "graph_id": graph_id,
        "graph_version": int(graph_version),
        "nodes": nodes,
        "edges": edges,
        "terms_sampled": len(rows),
        "packs_sampled": len(pack_ids),
        "linked_nodes_sampled": len(linked_refs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
