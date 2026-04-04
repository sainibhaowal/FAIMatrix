"""Phase 3 acceptance: FIG graph API surface exists, is wired, and returns contract shapes."""

from __future__ import annotations

import pathlib
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_isolated_runtime(monkeypatch, tenant_keys_json: str) -> None:
    db_path = tempfile.gettempdir() + f"/faim_fig_{uuid4().hex}.db"
    db_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", tenant_keys_json)
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")

    from runtime import context as runtime_context
    from runtime.config import reset_config
    from store.pg import session as pg_session

    monkeypatch.setattr(pg_session, "DEFAULT_DATABASE_URL", db_url, raising=False)
    monkeypatch.setattr(pg_session, "_SESSION_FACTORY_CACHE", {}, raising=False)
    monkeypatch.setattr(runtime_context, "_engine", None, raising=False)
    monkeypatch.setattr(runtime_context, "_engine_db_url", None, raising=False)
    monkeypatch.setattr(runtime_context, "_SessionLocal", None, raising=False)
    monkeypatch.setattr(runtime_context, "_raw_store_plain", None, raising=False)
    monkeypatch.setattr(runtime_context, "_raw_store_by_tenant", {}, raising=False)
    reset_config()


def _mk_client(monkeypatch) -> tuple[TestClient, dict, str, str]:
    """Return (client, headers, tenant_id, graph_id)."""
    tenant_id = f"tenant_fig_{uuid4().hex[:6]}"
    api_key = "fig_test_key"
    graph_id = f"graph_fig_{uuid4().hex[:8]}"

    _configure_isolated_runtime(
        monkeypatch,
        f'{{"{tenant_id}":["{api_key}"]}}',
    )

    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys

    reload_tenant_keys()

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}
    return client, headers, tenant_id, graph_id


def _seed_graph(tenant_id: str, graph_id: str) -> tuple[str, str, str]:
    """Seed two nodes and one edge. Returns (node_a_id, node_b_id, edge_id)."""
    from core.contracts.types import uuid7
    from runtime.context import close_session, get_repos

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        from store.pg.models_faim import EdgeModel, GraphVersionModel, NodeModel

        now = datetime.now(timezone.utc)
        a_id, b_id, e_id = uuid7(), uuid7(), uuid7()

        for uid, vh in ((a_id, "a" * 64), (b_id, "b" * 64)):
            session.add(
                NodeModel(
                    node_id=uid,
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    kind="atom",
                    vector_hash=vh,
                    raw_id=None,
                    block_id=None,
                    anchor_json={"title": f"Node {vh[:4]}"},
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
                edge_id=e_id,
                tenant_id=tenant_id,
                graph_id=graph_id,
                src_node_id=a_id,
                dst_node_id=b_id,
                kind="inheritance",
                weight=int(0.5 * 1e9),
                meta=None,
                created_at=now,
            )
        )

        # Ensure graph_version row exists.
        existing = (
            session.query(GraphVersionModel)
            .filter_by(graph_id=graph_id)
            .first()
        )
        if not existing:
            session.add(
                GraphVersionModel(
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    version=1,
                    reason="test seed",
                    updated_at=now,
                )
            )

        session.commit()
        return str(a_id), str(b_id), str(e_id)
    finally:
        close_session(session)


# ---------------------------------------------------------------------------
# 1. Static wiring tests
# ---------------------------------------------------------------------------


def test_graph_router_exists():
    from api.routers.graph import router

    assert router is not None


def test_graph_routes_present():
    from api.routers.graph import router

    paths = {route.path for route in router.routes}
    assert "/graph/surface" in paths
    assert "/graph/neighborhood" in paths
    assert "/graph/paths/explain" in paths


def test_app_includes_graph_router():
    candidates = [
        pathlib.Path("faim_native/api/app.py"),
        pathlib.Path("api/app.py"),
    ]
    app_path = next((p for p in candidates if p.exists()), None)
    assert app_path is not None, "cannot locate api/app.py"
    content = app_path.read_text()
    assert "graph_router" in content
    assert "include_router(graph_router" in content


# ---------------------------------------------------------------------------
# 2. Surface contract shape
# ---------------------------------------------------------------------------


def test_surface_returns_contract_shape(monkeypatch):
    client, headers, tenant_id, graph_id = _mk_client(monkeypatch)
    _seed_graph(tenant_id, graph_id)

    resp = client.get(
        f"/api/v1/graph/surface?graph_id={graph_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    # Top-level keys
    for key in ("snapshot", "nodes", "edges", "topology", "truncated", "controls"):
        assert key in body, f"missing key: {key}"

    # Snapshot shape
    snap = body["snapshot"]
    for key in ("graph_id", "graph_version", "graph_hash", "as_of", "consistent_read"):
        assert key in snap, f"snapshot missing: {key}"
    assert snap["graph_id"] == graph_id

    # Nodes shape
    assert len(body["nodes"]) >= 1
    node = body["nodes"][0]
    for key in ("node_id", "kind", "level", "vector_hash", "display"):
        assert key in node, f"node missing: {key}"
    assert "title" in node["display"]
    assert "title_source" in node["display"]
    assert "state" in node["display"]

    # Edges shape
    assert len(body["edges"]) >= 1
    edge = body["edges"][0]
    for key in ("edge_id", "src_node_id", "dst_node_id", "kind", "weight"):
        assert key in edge, f"edge missing: {key}"

    # Topology shape
    topo = body["topology"]
    assert topo is not None
    for key in ("node_count", "edge_count"):
        assert key in topo

    # Controls shape
    assert "similarity" in body["controls"]
    assert body["controls"]["similarity"]["mode"] == "none"


# ---------------------------------------------------------------------------
# 3. Neighborhood contract shape
# ---------------------------------------------------------------------------


def test_neighborhood_returns_contract_shape(monkeypatch):
    client, headers, tenant_id, graph_id = _mk_client(monkeypatch)
    node_a, node_b, _ = _seed_graph(tenant_id, graph_id)

    resp = client.get(
        f"/api/v1/graph/neighborhood?graph_id={graph_id}&node_id={node_a}",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    for key in ("snapshot", "seed_node_id", "depth_requested", "depth_effective",
                 "nodes", "edges", "distances", "truncated"):
        assert key in body, f"missing key: {key}"

    assert body["seed_node_id"] == node_a
    assert node_a in body["distances"]
    assert body["distances"][node_a] == 0


# ---------------------------------------------------------------------------
# 4. Explain contract shape
# ---------------------------------------------------------------------------


def test_explain_returns_contract_shape(monkeypatch):
    client, headers, tenant_id, graph_id = _mk_client(monkeypatch)
    node_a, node_b, _ = _seed_graph(tenant_id, graph_id)

    resp = client.post(
        f"/api/v1/graph/paths/explain?graph_id={graph_id}",
        headers=headers,
        json={"from_node_id": node_a, "to_node_id": node_b},
    )
    assert resp.status_code == 200
    body = resp.json()

    for key in ("snapshot", "from_node_id", "to_node_id", "path_found", "paths", "explanation"):
        assert key in body, f"missing key: {key}"

    assert body["path_found"] is True
    assert len(body["paths"]) >= 1
    assert body["explanation"]["hops"] >= 1
    assert body["explanation"]["relation_distance"] is not None


def test_explain_no_path_response(monkeypatch):
    """Two disconnected nodes should return path_found=false."""
    client, headers, tenant_id, graph_id = _mk_client(monkeypatch)

    # Seed two nodes with no edge between them.
    from core.contracts.types import uuid7
    from runtime.context import close_session, get_repos
    from store.pg.models_faim import GraphVersionModel, NodeModel

    repos = get_repos(tenant_id)
    session = repos["session"]
    now = datetime.now(timezone.utc)
    x_id, y_id = uuid7(), uuid7()
    try:
        for uid, vh in ((x_id, "x" * 64), (y_id, "y" * 64)):
            session.add(
                NodeModel(
                    node_id=uid, tenant_id=tenant_id, graph_id=graph_id,
                    kind="atom", vector_hash=vh, raw_id=None, block_id=None,
                    anchor_json=None, v_native=[0.0] * 256, opp_signature=None,
                    residual=0, level=0, touch_count=0, last_access=None,
                    created_at=now, updated_at=now,
                )
            )
        session.add(
            GraphVersionModel(
                tenant_id=tenant_id, graph_id=graph_id, version=1,
                reason="test", updated_at=now,
            )
        )
        session.commit()
    finally:
        close_session(session)

    resp = client.post(
        f"/api/v1/graph/paths/explain?graph_id={graph_id}",
        headers=headers,
        json={"from_node_id": str(x_id), "to_node_id": str(y_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["path_found"] is False
    assert body["paths"] == []
    assert body["explanation"]["relation_distance"] is None


# ---------------------------------------------------------------------------
# 5. Error handling
# ---------------------------------------------------------------------------


def test_surface_missing_graph_id(monkeypatch):
    client, headers, _, _ = _mk_client(monkeypatch)
    resp = client.get("/api/v1/graph/surface", headers=headers)
    assert resp.status_code == 400


def test_neighborhood_invalid_node_id(monkeypatch):
    client, headers, tenant_id, graph_id = _mk_client(monkeypatch)
    resp = client.get(
        f"/api/v1/graph/neighborhood?graph_id={graph_id}&node_id=not-a-uuid",
        headers=headers,
    )
    assert resp.status_code == 400


def test_neighborhood_node_not_found(monkeypatch):
    client, headers, tenant_id, graph_id = _mk_client(monkeypatch)
    fake_uuid = str(uuid4())
    resp = client.get(
        f"/api/v1/graph/neighborhood?graph_id={graph_id}&node_id={fake_uuid}",
        headers=headers,
    )
    assert resp.status_code == 404
