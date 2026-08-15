"""Graph artifact cleanup helpers (data-integrity layer).

Deletes nodes AND their dependent graph artifacts (edges, coactivations,
representations) atomically so a file delete never leaves orphaned edges.

Used by:
- ``api/routers/storage.py`` hard-delete path
- ``orchestration/jobs/storage_retention.py`` irreversible cleanup

Also exposes orphan-sweep helpers to repair graphs that were deleted before
these guarantees existed.

Cross-dialect notes: ``IN`` clauses are bound with ``bindparam(expanding=True)``
so both PostgreSQL and the SQLite fallback handle list parameters.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List

from sqlalchemy import bindparam, text

logger = logging.getLogger(__name__)


def _expanding(session: Any, sql: str, **params: Any):
    """Execute raw SQL with expanding IN-list bind parameters (PG+SQLite safe).

    Only values that are list/tuple are treated as expanding IN lists; scalar
    params are bound as-is.
    """
    stmt = text(sql)
    stmt = stmt.bindparams(
        *(bindparam(key, expanding=True) for key, val in params.items() if isinstance(val, (list, tuple)))
    )
    return session.execute(stmt, params)


def _as_uuid_list(values: Iterable[Any]) -> List[str]:
    """Normalize a mixed iterable of UUIDs/strings into str list."""
    seen: Dict[str, bool] = {}
    for v in values:
        if v is None:
            continue
        s = str(v)
        if s not in seen:
            seen[s] = True
    return list(seen.keys())


def resolve_node_ids_for_raw_ids(
    session: Any,
    tenant_id: str,
    graph_id: str,
    raw_ids: Iterable[Any],
) -> List[str]:
    """Resolve node_id strings for the given raw_id set within tenant+graph."""
    raw_list = _as_uuid_list(raw_ids)
    if not raw_list:
        return []
    rows = _expanding(
        session,
        "SELECT node_id FROM nodes "
        "WHERE tenant_id = :tenant_id AND graph_id = :graph_id "
        "AND raw_id IN :raw_ids",
        tenant_id=tenant_id,
        graph_id=graph_id,
        raw_ids=raw_list,
    ).fetchall()
    return [str(r[0]) for r in rows]


def delete_edges_touching_node_ids(
    session: Any,
    tenant_id: str,
    graph_id: str,
    node_ids: Iterable[Any],
) -> int:
    """Delete all edges where src OR dst is one of the given node_ids."""
    ids = _as_uuid_list(node_ids)
    if not ids:
        return 0
    result = _expanding(
        session,
        "DELETE FROM edges WHERE tenant_id = :tenant_id AND graph_id = :graph_id "
        "AND (src_node_id IN :ids OR dst_node_id IN :ids)",
        tenant_id=tenant_id,
        graph_id=graph_id,
        ids=ids,
    )
    return result.rowcount or 0


def delete_coactivations_referencing_nodes(
    session: Any,
    tenant_id: str,
    graph_id: str,
    node_ids: Iterable[Any],
) -> int:
    """Delete coactivation sets whose members include any of the given node_ids.

    ``members`` is stored as a JSON array of node_id strings (JSONB in PG,
    TEXT-encoded JSON in the SQLite fallback), so membership is checked in
    Python for cross-dialect safety.
    """
    ids = _as_uuid_list(node_ids)
    if not ids:
        return 0
    wanted = set(ids)

    rows = session.execute(
        text(
            "SELECT signature, members FROM coactivations "
            "WHERE tenant_id = :tenant_id AND graph_id = :graph_id"
        ),
        {"tenant_id": tenant_id, "graph_id": graph_id},
    ).fetchall()

    doomed: List[str] = []
    for signature, members_raw in rows:
        members: List[Any] = []
        if isinstance(members_raw, str):
            try:
                members = json.loads(members_raw)
            except (TypeError, ValueError):
                members = []
        elif isinstance(members_raw, (list, tuple)):
            members = list(members_raw)
        member_ids = {str(m) for m in members}
        if member_ids & wanted:
            doomed.append(str(signature))

    if not doomed:
        return 0
    _expanding(
        session,
        "DELETE FROM coactivations WHERE tenant_id = :tenant_id "
        "AND graph_id = :graph_id AND signature IN :signatures",
        tenant_id=tenant_id,
        graph_id=graph_id,
        signatures=doomed,
    )
    return len(doomed)


def delete_representations_for_nodes(
    session: Any,
    tenant_id: str,
    graph_id: str,
    node_ids: Iterable[Any],
) -> int:
    """Delete node_repr_v2 rows for the given node_ids."""
    ids = _as_uuid_list(node_ids)
    if not ids:
        return 0
    result = _expanding(
        session,
        "DELETE FROM node_repr_v2 WHERE tenant_id = :tenant_id "
        "AND graph_id = :graph_id AND node_id IN :ids",
        tenant_id=tenant_id,
        graph_id=graph_id,
        ids=ids,
    )
    return result.rowcount or 0


def delete_nodes_for_raw_ids(
    session: Any,
    tenant_id: str,
    graph_id: str,
    raw_ids: Iterable[Any],
) -> int:
    """Delete nodes belonging to the given raw_ids within tenant+graph."""
    raw_list = _as_uuid_list(raw_ids)
    if not raw_list:
        return 0
    result = _expanding(
        session,
        "DELETE FROM nodes WHERE tenant_id = :tenant_id "
        "AND graph_id = :graph_id AND raw_id IN :raw_ids",
        tenant_id=tenant_id,
        graph_id=graph_id,
        raw_ids=raw_list,
    )
    return result.rowcount or 0


def purge_graph_artifacts_for_raw_ids(
    session: Any,
    tenant_id: str,
    graph_id: str,
    raw_ids: Iterable[Any],
) -> Dict[str, int]:
    """Atomically remove all graph artifacts for the given raw files.

    Order matters (children first):
      1. edges touching the nodes
      2. coactivations referencing the nodes
      3. node_repr_v2 rows
      4. the nodes themselves

    Returns a summary dict of deleted counts for audit/logging.
    """
    raw_list = _as_uuid_list(raw_ids)
    if not raw_list:
        return {"edges": 0, "coactivations": 0, "representations": 0, "nodes": 0}

    node_ids = resolve_node_ids_for_raw_ids(session, tenant_id, graph_id, raw_list)

    edges = delete_edges_touching_node_ids(session, tenant_id, graph_id, node_ids)
    coacts = delete_coactivations_referencing_nodes(
        session, tenant_id, graph_id, node_ids
    )
    reps = delete_representations_for_nodes(session, tenant_id, graph_id, node_ids)
    nodes = delete_nodes_for_raw_ids(session, tenant_id, graph_id, raw_list)

    summary = {
        "edges": edges,
        "coactivations": coacts,
        "representations": reps,
        "nodes": nodes,
    }
    logger.info(
        "graph artifact purge",
        extra={
            "tenant_id": tenant_id,
            "graph_id": graph_id,
            "op": "purge_graph_artifacts",
            "status": "ok",
            "deleted": summary,
        },
    )
    return summary


def find_orphan_edges(
    session: Any,
    tenant_id: str,
    graph_id: str,
    limit: int = 5000,
) -> List[str]:
    """Return edge_ids whose src or dst node no longer exists (orphans).

    Same anti-join predicate as ``sweep_orphan_edges`` but read-only so
    callers can report health before sweeping.
    """
    rows = session.execute(
        text(
            "SELECT edge_id FROM edges WHERE tenant_id = :tenant_id "
            "AND graph_id = :graph_id "
            "AND ( "
            "  NOT EXISTS (SELECT 1 FROM nodes n WHERE n.node_id = edges.src_node_id AND n.tenant_id = edges.tenant_id) "
            "  OR NOT EXISTS (SELECT 1 FROM nodes n WHERE n.node_id = edges.dst_node_id AND n.tenant_id = edges.tenant_id) "
            ") LIMIT :limit"
        ),
        {"tenant_id": tenant_id, "graph_id": graph_id, "limit": limit},
    ).fetchall()
    return [str(r[0]) for r in rows]


def find_orphan_coactivations(
    session: Any,
    tenant_id: str,
    graph_id: str,
) -> List[str]:
    """Return signatures of coactivation sets with ANY missing member node.

    Same semantics as ``sweep_orphan_coactivations`` but read-only. Membership
    is JSON-encoded, evaluated in Python per row for cross-dialect safety.
    """
    rows = session.execute(
        text(
            "SELECT signature, members FROM coactivations "
            "WHERE tenant_id = :tenant_id AND graph_id = :graph_id"
        ),
        {"tenant_id": tenant_id, "graph_id": graph_id},
    ).fetchall()

    orphaned: List[str] = []
    for signature, members_raw in rows:
        members: List[Any] = []
        if isinstance(members_raw, str):
            try:
                members = json.loads(members_raw)
            except (TypeError, ValueError):
                members = []
        elif isinstance(members_raw, (list, tuple)):
            members = list(members_raw)
        member_ids = [str(m) for m in members]
        if not member_ids:
            continue
        found = _expanding(
            session,
            "SELECT count(*) FROM nodes WHERE tenant_id = :tenant_id "
            "AND graph_id = :graph_id AND node_id IN :ids",
            tenant_id=tenant_id,
            graph_id=graph_id,
            ids=member_ids,
        ).scalar()
        if found != len(member_ids):
            orphaned.append(str(signature))
    return orphaned


def sweep_orphan_edges(
    session: Any,
    tenant_id: str,
    graph_id: str,
    limit: int = 5000,
) -> int:
    """Delete edges whose src or dst node no longer exists (orphans).

    SQL-level anti-join keeps this O(1) per candidate batch and works on both
    Postgres and SQLite.
    """
    result = session.execute(
        text(
            "DELETE FROM edges WHERE tenant_id = :tenant_id AND graph_id = :graph_id "
            "AND ( "
            "  NOT EXISTS (SELECT 1 FROM nodes n WHERE n.node_id = edges.src_node_id AND n.tenant_id = edges.tenant_id) "
            "  OR NOT EXISTS (SELECT 1 FROM nodes n WHERE n.node_id = edges.dst_node_id AND n.tenant_id = edges.tenant_id) "
            ") "
            "AND edge_id IN (SELECT edge_id FROM edges e2 WHERE e2.tenant_id = :tenant_id "
            "                AND e2.graph_id = :graph_id "
            "                AND (NOT EXISTS (SELECT 1 FROM nodes n WHERE n.node_id = e2.src_node_id AND n.tenant_id = e2.tenant_id) "
            "                     OR NOT EXISTS (SELECT 1 FROM nodes n WHERE n.node_id = e2.dst_node_id AND n.tenant_id = e2.tenant_id)) "
            "                LIMIT :limit)"
        ),
        {"tenant_id": tenant_id, "graph_id": graph_id, "limit": limit},
    )
    return result.rowcount or 0


def sweep_orphan_coactivations(
    session: Any,
    tenant_id: str,
    graph_id: str,
) -> int:
    """Delete coactivation sets where ANY member node no longer exists.

    Matches ``delete_coactivations_referencing_nodes`` semantics (intersection
    against existing nodes), so a sweep converges on the same state a purge
    would produce. Membership is JSON-encoded, evaluated in Python per row.
    """
    rows = session.execute(
        text(
            "SELECT signature, members FROM coactivations "
            "WHERE tenant_id = :tenant_id AND graph_id = :graph_id"
        ),
        {"tenant_id": tenant_id, "graph_id": graph_id},
    ).fetchall()

    doomed: List[str] = []
    for signature, members_raw in rows:
        members: List[Any] = []
        if isinstance(members_raw, str):
            try:
                members = json.loads(members_raw)
            except (TypeError, ValueError):
                members = []
        elif isinstance(members_raw, (list, tuple)):
            members = list(members_raw)
        member_ids = [str(m) for m in members]
        if not member_ids:
            continue
        found = _expanding(
            session,
            "SELECT count(*) FROM nodes WHERE tenant_id = :tenant_id "
            "AND graph_id = :graph_id AND node_id IN :ids",
            tenant_id=tenant_id,
            graph_id=graph_id,
            ids=member_ids,
        ).scalar()
        if found != len(member_ids):
            doomed.append(str(signature))

    if not doomed:
        return 0
    _expanding(
        session,
        "DELETE FROM coactivations WHERE tenant_id = :tenant_id "
        "AND graph_id = :graph_id AND signature IN :signatures",
        tenant_id=tenant_id,
        graph_id=graph_id,
        signatures=doomed,
    )
    return len(doomed)


__all__ = [
    "purge_graph_artifacts_for_raw_ids",
    "resolve_node_ids_for_raw_ids",
    "delete_edges_touching_node_ids",
    "delete_coactivations_referencing_nodes",
    "delete_representations_for_nodes",
    "delete_nodes_for_raw_ids",
    "sweep_orphan_edges",
    "sweep_orphan_coactivations",
    "find_orphan_edges",
    "find_orphan_coactivations",
]
