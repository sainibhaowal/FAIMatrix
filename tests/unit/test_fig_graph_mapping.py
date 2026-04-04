"""Unit tests for FIG graph router mapping and path helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.fig_graph_core import (
    SURFACE_NODE_DEF,
    _clamp_int,
    _parse_edge_kinds_csv,
    node_display_payload,
    shortest_path_undirected,
)
from core.contracts.types import uuid7
from store.pg.models_faim import EdgeModel, NodeModel, create_all_tables


def test_clamp_int_defaults_when_below_min():
    assert _clamp_int(0, default=SURFACE_NODE_DEF, lo=1, hi=500) == SURFACE_NODE_DEF


def test_clamp_int_caps_high():
    assert _clamp_int(9999, default=1, lo=1, hi=10) == 10


def test_parse_edge_kinds_csv():
    assert _parse_edge_kinds_csv("inheritance,opposition") == {
        "inheritance",
        "opposition",
    }
    assert _parse_edge_kinds_csv("bogus,inheritance") == {"inheritance"}


def test_node_display_anchor_title():
    now = datetime.now(timezone.utc)
    nid = uuid7()
    n = NodeModel(
        node_id=nid,
        tenant_id="t",
        graph_id="g",
        kind="atom",
        vector_hash="ab" * 32,
        raw_id=None,
        block_id=None,
        anchor_json={"title": "Hello"},
        v_native=[0.0] * 256,
        opp_signature=None,
        residual=0,
        level=0,
        touch_count=10,
        last_access=now,
        created_at=now,
        updated_at=now,
    )
    d = node_display_payload(n)
    assert d["title"] == "Hello"
    assert d["title_source"] == "anchor"
    assert d["state"] == "active"


def test_clamp_int_within_range():
    assert _clamp_int(50, default=SURFACE_NODE_DEF, lo=1, hi=500) == 50


def test_clamp_int_at_boundaries():
    assert _clamp_int(1, default=SURFACE_NODE_DEF, lo=1, hi=500) == 1
    assert _clamp_int(500, default=SURFACE_NODE_DEF, lo=1, hi=500) == 500


def test_parse_edge_kinds_empty():
    assert _parse_edge_kinds_csv("") == set()
    assert _parse_edge_kinds_csv(None) == set()


def test_node_display_fallback_block_id():
    now = datetime.now(timezone.utc)
    from core.contracts.types import uuid7

    n = NodeModel(
        node_id=uuid7(), tenant_id="t", graph_id="g", kind="atom",
        vector_hash="cc" * 32, raw_id=None, block_id="my_block_42",
        anchor_json=None, v_native=[0.0] * 256, opp_signature=None,
        residual=0, level=0, touch_count=0, last_access=None,
        created_at=now, updated_at=now,
    )
    d = node_display_payload(n)
    assert d["title"] == "my_block_42"
    assert d["title_source"] == "block_id"


def test_node_display_fallback_vector_hash():
    now = datetime.now(timezone.utc)
    from core.contracts.types import uuid7

    n = NodeModel(
        node_id=uuid7(), tenant_id="t", graph_id="g", kind="atom",
        vector_hash="dd" * 32, raw_id=None, block_id=None,
        anchor_json=None, v_native=[0.0] * 256, opp_signature=None,
        residual=0, level=0, touch_count=0, last_access=None,
        created_at=now, updated_at=now,
    )
    d = node_display_payload(n)
    assert d["title_source"] == "vector_hash"
    assert "atom" in d["title"]


def test_node_display_state_cold():
    from datetime import timedelta

    from core.contracts.types import uuid7

    old = datetime.now(timezone.utc) - timedelta(days=200)
    n = NodeModel(
        node_id=uuid7(), tenant_id="t", graph_id="g", kind="atom",
        vector_hash="ee" * 32, raw_id=None, block_id=None,
        anchor_json=None, v_native=[0.0] * 256, opp_signature=None,
        residual=0, level=0, touch_count=0, last_access=old,
        created_at=old, updated_at=old,
    )
    d = node_display_payload(n)
    assert d["state"] == "cold"


def test_node_display_state_unknown():
    from core.contracts.types import uuid7

    now = datetime.now(timezone.utc)
    n = NodeModel(
        node_id=uuid7(), tenant_id="t", graph_id="g", kind="atom",
        vector_hash="ff" * 32, raw_id=None, block_id=None,
        anchor_json=None, v_native=[0.0] * 256, opp_signature=None,
        residual=0, level=0, touch_count=2, last_access=None,
        created_at=now, updated_at=now,
    )
    d = node_display_payload(n)
    assert d["state"] == "unknown"


def test_shortest_path_inheritance_chain():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    tenant_id = "t_fig_path"
    graph_id = "g_fig_path"
    now = datetime.now(timezone.utc)
    a, b, c = uuid7(), uuid7(), uuid7()
    try:
        for uid, vh in ((a, "a" * 64), (b, "b" * 64), (c, "c" * 64)):
            session.add(
                NodeModel(
                    node_id=uid,
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    kind="atom",
                    vector_hash=vh,
                    raw_id=None,
                    block_id=None,
                    anchor_json=None,
                    v_native=[0.0] * 256,
                    opp_signature=None,
                    residual=0,
                    level=0,
                    touch_count=1,
                    last_access=now,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.add(
            EdgeModel(
                edge_id=uuid7(),
                tenant_id=tenant_id,
                graph_id=graph_id,
                src_node_id=a,
                dst_node_id=b,
                kind="inheritance",
                weight=int(0.5 * 1e9),
                meta=None,
                created_at=now,
            )
        )
        session.add(
            EdgeModel(
                edge_id=uuid7(),
                tenant_id=tenant_id,
                graph_id=graph_id,
                src_node_id=b,
                dst_node_id=c,
                kind="inheritance",
                weight=int(0.5 * 1e9),
                meta=None,
                created_at=now,
            )
        )
        session.commit()

        out = shortest_path_undirected(
            session,
            tenant_id,
            graph_id,
            a,
            c,
            {"inheritance"},
            12,
        )
        assert out is not None
        nodes, edges = out
        assert [str(x) for x in nodes] == [str(a), str(b), str(c)]
        assert len(edges) == 2
    finally:
        session.close()
