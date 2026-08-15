"""Unit tests: graph artifact cleanup on file delete (orphan-edge prevention)."""

from __future__ import annotations

import json
from uuid import uuid4

import sqlalchemy as sa


def _insert_graph_artifacts(session, tenant_id: str, graph_id: str, raw_id):
    from store.pg.models_faim import NodeModel

    n1 = NodeModel(
        node_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash=f"v1-{raw_id}",
        raw_id=str(raw_id),
        v_native=[0.0] * 4,
    )
    n2 = NodeModel(
        node_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash=f"v2-{raw_id}",
        raw_id=str(raw_id),
        v_native=[0.0] * 4,
    )
    n3 = NodeModel(
        node_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash="v3-keep",
        raw_id=str(uuid4()),
        v_native=[0.0] * 4,
    )
    n4 = NodeModel(
        node_id=uuid4(),
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="atom",
        vector_hash="v4-keep",
        raw_id=str(uuid4()),
        v_native=[0.0] * 4,
    )
    session.add_all([n1, n2, n3, n4])
    session.flush()

    # Edges: n1<->n2 (both deleted: gone), n1<->n3 (deleted: gone),
    #        n3<->n4 (both kept: should survive)
    session.execute(
        sa.text(
            "INSERT INTO edges (edge_id, tenant_id, graph_id, src_node_id, dst_node_id, kind, weight, created_at) "
            "VALUES (:e1, :t, :g, :s1, :d1, 'related', 1, CURRENT_TIMESTAMP), "
            "(:e2, :t, :g, :s1, :d2, 'related', 1, CURRENT_TIMESTAMP), "
            "(:e3, :t, :g, :s3, :d4, 'related', 1, CURRENT_TIMESTAMP)"
        ),
        {
            "e1": str(uuid4()),
            "e2": str(uuid4()),
            "e3": str(uuid4()),
            "t": tenant_id,
            "g": graph_id,
            "s1": str(n1.node_id),
            "d1": str(n2.node_id),
            "d2": str(n3.node_id),
            "s3": str(n3.node_id),
            "d4": str(n4.node_id),
        },
    )
    # Coactivation referencing n1,n2 (doomed) and n2,n3 (doomed) and n3 alone (kept)
    session.execute(
        sa.text(
            "INSERT INTO coactivations (tenant_id, graph_id, signature, members, coactivation_count, invented) "
            "VALUES (:t, :g, :sig1, :m1, 2, FALSE), (:t, :g, :sig2, :m2, 1, FALSE)"
        ),
        {
            "t": tenant_id,
            "g": graph_id,
            "sig1": "sig-a1",
            "m1": json.dumps([str(n1.node_id), str(n2.node_id)]),
            "sig2": "sig-b1",
            "m2": json.dumps([str(n2.node_id), str(n3.node_id)]),
        },
    )
    session.commit()
    return n1, n2, n3


def _counts(session, tenant_id: str, graph_id: str) -> dict:
    from store.pg.models_faim import (
        CoactivationModel,
        EdgeModel,
        NodeModel,
    )

    node_count = session.query(NodeModel).filter(
        NodeModel.tenant_id == tenant_id, NodeModel.graph_id == graph_id
    ).count()
    edge_count = session.query(EdgeModel).filter(
        EdgeModel.tenant_id == tenant_id, EdgeModel.graph_id == graph_id
    ).count()
    coact_count = session.query(CoactivationModel).filter(
        CoactivationModel.tenant_id == tenant_id,
        CoactivationModel.graph_id == graph_id,
    ).count()
    return {"nodes": node_count, "edges": edge_count, "coactivations": coact_count}


def test_purge_graph_artifacts_removes_edges_and_coactivations(db_session):
    from store.pg.graph_cleanup import purge_graph_artifacts_for_raw_ids

    tenant_id = "tenant_cleanup_unit"
    graph_id = "graph-cleanup-unit"
    raw_id = uuid4()

    _insert_graph_artifacts(db_session, tenant_id, graph_id, raw_id)
    before = _counts(db_session, tenant_id, graph_id)
    assert before["nodes"] == 4
    assert before["edges"] == 3
    assert before["coactivations"] == 2

    summary = purge_graph_artifacts_for_raw_ids(
        session=db_session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        raw_ids=[raw_id],
    )
    db_session.commit()

    assert summary["edges"] == 2  # n1<->n2 and n1<->n3 die
    assert summary["coactivations"] == 2  # both reference deleted nodes
    assert summary["nodes"] == 2  # n1, n2 deleted; n3, n4 kept
    assert summary["representations"] == 0

    after = _counts(db_session, tenant_id, graph_id)
    assert after["nodes"] == 2
    assert after["edges"] == 1  # surviving n3<->n4 edge intact
    assert after["coactivations"] == 0


def test_sweep_orphan_edges_and_coactivations_repairs(db_session):
    from store.pg.graph_cleanup import (
        sweep_orphan_coactivations,
        sweep_orphan_edges,
    )

    tenant_id = "tenant_sweep_unit"
    graph_id = "graph-sweep-unit"
    raw_id = uuid4()

    n1, n2, _n3 = _insert_graph_artifacts(db_session, tenant_id, graph_id, raw_id)

    # Simulate historical damage: delete n1 and n2 directly WITHOUT edge cleanup
    db_session.execute(
        sa.text(
            "DELETE FROM nodes WHERE tenant_id=:t AND graph_id=:g "
            "AND node_id IN (:a, :b)"
        ),
        {"t": tenant_id, "g": graph_id, "a": str(n1.node_id), "b": str(n2.node_id)},
    )
    db_session.commit()

    edges = sweep_orphan_edges(db_session, tenant_id, graph_id)
    coacts = sweep_orphan_coactivations(db_session, tenant_id, graph_id)
    db_session.commit()

    assert edges == 2  # n1/n2-related edges now reference missing nodes
    assert coacts == 2

    after = _counts(db_session, tenant_id, graph_id)
    assert after["nodes"] == 2
    assert after["edges"] == 1  # kept n3<->n4 edge survives
    assert after["coactivations"] == 0


def test_purge_is_idempotent(db_session):
    from store.pg.graph_cleanup import purge_graph_artifacts_for_raw_ids

    tenant_id = "tenant_cleanup_idem"
    graph_id = "graph-cleanup-idem"
    raw_id = uuid4()
    _insert_graph_artifacts(db_session, tenant_id, graph_id, raw_id)

    purge_graph_artifacts_for_raw_ids(
        session=db_session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        raw_ids=[raw_id],
    )
    db_session.commit()
    summary2 = purge_graph_artifacts_for_raw_ids(
        session=db_session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        raw_ids=[raw_id],
    )
    db_session.commit()

    assert summary2["edges"] == 0
    assert summary2["nodes"] == 0
    assert _counts(db_session, tenant_id, graph_id) == {
        "nodes": 2,  # n3, n4 kept
        "edges": 1,  # n3<->n4 survives
        "coactivations": 0,
    }
