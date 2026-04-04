"""Phase 3 acceptance: FIG graph router auth enforcement and tenant isolation."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_isolated_runtime(monkeypatch, tenant_keys_json: str) -> None:
    db_path = tempfile.gettempdir() + f"/faim_fig_iso_{uuid4().hex}.db"
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


def _seed_nodes_for_tenant(tenant_id: str, graph_id: str) -> tuple[str, str]:
    """Seed two connected nodes for a tenant. Returns (node_a_id, node_b_id)."""
    from core.contracts.types import uuid7
    from runtime.context import close_session, get_repos
    from store.pg.models_faim import EdgeModel, GraphVersionModel, NodeModel

    repos = get_repos(tenant_id)
    session = repos["session"]
    now = datetime.now(timezone.utc)
    a_id, b_id = uuid7(), uuid7()
    try:
        for uid, vh in ((a_id, "a" * 64), (b_id, "b" * 64)):
            session.add(
                NodeModel(
                    node_id=uid, tenant_id=tenant_id, graph_id=graph_id,
                    kind="atom", vector_hash=vh, raw_id=None, block_id=None,
                    anchor_json={"title": f"Node {vh[:4]}"},
                    v_native=[0.0] * 256, opp_signature=None,
                    residual=0, level=0, touch_count=1,
                    last_access=now, created_at=now, updated_at=now,
                )
            )
        session.add(
            EdgeModel(
                edge_id=uuid7(), tenant_id=tenant_id, graph_id=graph_id,
                src_node_id=a_id, dst_node_id=b_id,
                kind="inheritance", weight=int(0.5 * 1e9),
                meta=None, created_at=now,
            )
        )
        existing = session.query(GraphVersionModel).filter_by(graph_id=graph_id).first()
        if not existing:
            session.add(
                GraphVersionModel(
                    tenant_id=tenant_id, graph_id=graph_id,
                    version=1, reason="seed", updated_at=now,
                )
            )
        session.commit()
        return str(a_id), str(b_id)
    finally:
        close_session(session)


# ---------------------------------------------------------------------------
# 1. Auth enforcement — all graph routes require auth
# ---------------------------------------------------------------------------


def test_all_graph_routes_require_auth(monkeypatch):
    _configure_isolated_runtime(monkeypatch, '{"tenant_auth":["key_auth"]}')

    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from api.routers.graph import router as graph_router

    reload_tenant_keys()
    client = TestClient(create_app())

    for route in graph_router.routes:
        if not isinstance(route, APIRoute):
            continue
        path = "/api/v1" + route.path
        for method in sorted(route.methods or []):
            if method in {"HEAD", "OPTIONS"}:
                continue
            resp = client.request(method, path)
            assert resp.status_code == 401, (
                f"{method} {path} should require auth, got {resp.status_code}"
            )


# ---------------------------------------------------------------------------
# 2. Surface tenant isolation
# ---------------------------------------------------------------------------


def test_graph_surface_tenant_isolation(monkeypatch):
    # Use distinct graph_ids per tenant to avoid graph_version PK collision
    # (graph_version uses graph_id alone as PK, not (tenant_id, graph_id)).
    graph_id_a = f"graph_iso_a_{uuid4().hex[:8]}"
    graph_id_b = f"graph_iso_b_{uuid4().hex[:8]}"
    _configure_isolated_runtime(
        monkeypatch,
        '{"tenant_a":["key_a"],"tenant_b":["key_b"]}',
    )

    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys

    reload_tenant_keys()
    client = TestClient(create_app())

    headers_a = {"X-Tenant-Id": "tenant_a", "X-Api-Key": "key_a"}
    headers_b = {"X-Tenant-Id": "tenant_b", "X-Api-Key": "key_b"}

    # Seed nodes for tenant_a only.
    _seed_nodes_for_tenant("tenant_a", graph_id_a)

    # Tenant A sees its nodes.
    resp_a = client.get(
        f"/api/v1/graph/surface?graph_id={graph_id_a}", headers=headers_a,
    )
    assert resp_a.status_code == 200
    assert len(resp_a.json()["nodes"]) >= 1

    # Tenant B queries its own graph_id — sees nothing (no data seeded for B).
    resp_b = client.get(
        f"/api/v1/graph/surface?graph_id={graph_id_b}", headers=headers_b,
    )
    assert resp_b.status_code == 200
    assert len(resp_b.json()["nodes"]) == 0


# ---------------------------------------------------------------------------
# 3. Neighborhood tenant isolation
# ---------------------------------------------------------------------------


def test_graph_neighborhood_tenant_isolation(monkeypatch):
    graph_id = f"graph_iso_nb_{uuid4().hex[:8]}"
    _configure_isolated_runtime(
        monkeypatch,
        '{"tenant_a":["key_a"],"tenant_b":["key_b"]}',
    )

    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys

    reload_tenant_keys()
    client = TestClient(create_app())

    headers_b = {"X-Tenant-Id": "tenant_b", "X-Api-Key": "key_b"}

    node_a, _ = _seed_nodes_for_tenant("tenant_a", graph_id)

    # Tenant B cannot expand tenant A's node.
    resp = client.get(
        f"/api/v1/graph/neighborhood?graph_id={graph_id}&node_id={node_a}",
        headers=headers_b,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Explain tenant isolation
# ---------------------------------------------------------------------------


def test_graph_explain_tenant_isolation(monkeypatch):
    graph_id = f"graph_iso_ex_{uuid4().hex[:8]}"
    _configure_isolated_runtime(
        monkeypatch,
        '{"tenant_a":["key_a"],"tenant_b":["key_b"]}',
    )

    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys

    reload_tenant_keys()
    client = TestClient(create_app())

    headers_b = {"X-Tenant-Id": "tenant_b", "X-Api-Key": "key_b"}

    node_a, node_b = _seed_nodes_for_tenant("tenant_a", graph_id)

    # Tenant B cannot explain paths between tenant A's nodes.
    resp = client.post(
        f"/api/v1/graph/paths/explain?graph_id={graph_id}",
        headers=headers_b,
        json={"from_node_id": node_a, "to_node_id": node_b},
    )
    assert resp.status_code == 404
