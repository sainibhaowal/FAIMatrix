"""Phase EV-C acceptance: invention flow topology surface.

GET /api/v1/evolve/invention/flow returns real graph-derived pipeline
stages (atoms, macros, merges) with tenant isolation and no mutation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient


def _mk_client(monkeypatch, *, tenant_keys_json: str, database_url: str) -> TestClient:
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from runtime import context as runtime_context
    from runtime.config import reset_config
    from store.pg import session as pg_session

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", tenant_keys_json)
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "false")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "manual")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")
    monkeypatch.setattr(pg_session, "_SESSION_FACTORY_CACHE", {}, raising=False)
    monkeypatch.setattr(runtime_context, "_engine", None, raising=False)
    monkeypatch.setattr(runtime_context, "_engine_db_url", None, raising=False)
    monkeypatch.setattr(runtime_context, "_SessionLocal", None, raising=False)
    reset_config()
    reload_tenant_keys()
    return TestClient(create_app())


def _make_admin_jwt(*, user_id: str, email: str, secret: str, graph_id: str) -> str:
    now = datetime.utcnow()
    claims = {
        "sub": user_id,
        "id": user_id,
        "email": email,
        "graphId": graph_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def test_phase_ev_c_invention_flow_route_present():
    from api.routers.evolve import router

    paths = {route.path for route in router.routes}
    assert "/evolve/invention/flow" in paths


def _seed_graph(session, tenant_id: str, graph_id: str) -> dict:
    """Seed atoms + one macro + one opposition merge for the flow view."""
    from core.engine_native import FAIMNativeEngine
    from encoding.text_vectorizer import vectorize_blocks
    from perception.router import route_extraction
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo

    node_repo = NodeRepo(session, tenant_id=tenant_id)
    edge_repo = EdgeRepo(session, tenant_id=tenant_id)
    event_repo = EventRepo(tenant_id=tenant_id)
    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
    engine_repo = FAIMNativeEngine(
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        graph_version_repo=gv_repo,
    )

    def _write(text: str, raw_id: str):
        blocks = route_extraction(text.encode("utf-8"), f"{raw_id}.txt", raw_id)
        vectors = vectorize_blocks(blocks)
        engine_repo.write_atoms(graph_id=graph_id, vectors=vectors)

    _write(
        "NGINX reverse proxy load balancing across backend replicas", "raw-a"
    )
    _write(
        "PgBouncer connection pooling keeps database session count bounded", "raw-b"
    )
    _write(
        "Redis session cache TTL expires idle memory entries", "raw-c"
    )

    atoms = node_repo.list_atoms(graph_id=graph_id, limit=10)
    assert len(atoms) >= 2

    # Macro over first two atoms (skip lambda check for deterministic test).
    from core.dynamics.invention_native import invent_macro

    macro_id = invent_macro(
        graph_id=graph_id,
        member_ids=[atoms[0].node_id, atoms[1].node_id],
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        skip_lambda_check=True,
        coactivation_count=4,
    )
    assert macro_id is not None

    # Opposition merge between atom 0 (winner) and atom 2 (loser).
    edge_repo.add_opposition_edge(
        graph_id=graph_id,
        a_id=atoms[0].node_id,
        b_id=atoms[2].node_id,
        weight=0.97,
        meta={
            "winner_hash": atoms[0].vector_hash,
            "loser_hash": atoms[2].vector_hash,
            "merge_reason": "high_similarity",
        },
    )

    # Emit a completed cycle + its merge so the flow view can flag "recent".
    event_repo.emit(
        session=session,
        graph_id=graph_id,
        kind="EVOLUTION_MERGE",
        payload={
            "winner_id": str(atoms[0].node_id),
            "loser_id": str(atoms[2].node_id),
            "score": 0.97,
            "selector": "legacy_hash",
        },
    )
    event_repo.emit(
        session=session,
        graph_id=graph_id,
        kind="EVOLUTION_COMPLETE",
        payload={"version": 2, "merges": 1, "prunes": 0},
    )

    session.commit()
    return {"atoms": atoms, "macro_id": macro_id}


def test_phase_ev_c_invention_flow_returns_real_stages(monkeypatch, tmp_path):
    from runtime.context import close_session, get_repos

    tenant_a = f"tenant_evc_a_{uuid4().hex[:6]}"
    key_a = "key_evc_a"
    graph_id = f"graph_evc_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'evc_flow.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"]}}',
        database_url=database_url,
    )

    repos = get_repos(tenant_a)
    session = repos["session"]
    try:
        _seed_graph(session, tenant_a, graph_id)
    finally:
        close_session(session)

    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}
    response = client.get(
        f"/api/v1/evolve/invention/flow?graph_id={graph_id}",
        headers=headers_a,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["graph_id"] == graph_id
    assert body["tenant_id"] == tenant_a
    assert body["node_count"] >= 3
    assert body["macro_count"] >= 1
    assert body["merge_count"] == 1

    stages = body["stages"]
    assert len(stages["atoms"]) >= 2
    assert all(node["stage"] == "atom" for node in stages["atoms"])
    assert all(node["title"] for node in stages["atoms"])
    assert all(node["status"] == "active" for node in stages["atoms"])

    assert len(stages["macros"]) >= 1
    macro = stages["macros"][0]
    assert macro["stage"] == "macro"
    assert macro["status"] == "synthesized"
    assert macro["child_count"] >= 2
    assert macro["children_details"]
    assert all("similarity" in child for child in macro["children_details"])

    assert len(stages["merges"]) == 2  # winner + pruned
    statuses = {node["status"] for node in stages["merges"]}
    assert statuses == {"winner", "pruned"}

    winner = next(n for n in stages["merges"] if n["status"] == "winner")
    pruned = next(n for n in stages["merges"] if n["status"] == "pruned")

    # Legacy fallback verdict is surfaced as a decision.
    assert winner["decision"]["selector"] == "legacy_hash"
    assert winner["decision"]["score_winner"] >= winner["decision"]["score_loser"]
    assert winner["decision"]["score_winner"] > 0
    assert "components_winner" in winner["decision"]

    # The seeded merge is flagged as touched by the latest completed cycle.
    assert winner["recent"] is True
    assert pruned["recent"] is True

    # Version history: one completed cycle owning the seeded merge.
    vresponse = client.get(
        f"/api/v1/evolve/invention/versions?graph_id={graph_id}",
        headers=headers_a,
    )
    assert vresponse.status_code == 200
    vbody = vresponse.json()
    assert vbody["graph_id"] == graph_id
    assert vbody["tenant_id"] == tenant_a
    assert vbody["current_version"] >= 1
    assert len(vbody["versions"]) == 1
    row = vbody["versions"][0]
    assert row["version"] == 2
    assert row["merges"] == 1
    assert "diagnostics" in row
    assert len(row["changes"]) == 1
    change = row["changes"][0]
    assert change["selector"] == "legacy_hash"
    assert change["score"] == pytest.approx(0.97, abs=1e-3)
    assert change["winner_label"]
    assert change["loser_label"]
    assert change["winner_id"] != change["loser_id"]


def test_phase_ev_c_invention_flow_empty_graph(monkeypatch, tmp_path):
    from runtime.context import close_session

    tenant_a = f"tenant_evc_empty_{uuid4().hex[:6]}"
    key_a = "key_evc_empty"
    graph_id = f"graph_evc_empty_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'evc_empty.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"]}}',
        database_url=database_url,
    )

    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}
    response = client.get(
        f"/api/v1/evolve/invention/flow?graph_id={graph_id}",
        headers=headers_a,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["node_count"] == 0
    assert body["stages"]["atoms"] == []
    assert body["stages"]["macros"] == []
    assert body["stages"]["merges"] == []


def test_phase_ev_c_invention_flow_tenant_isolation(monkeypatch, tmp_path):
    from runtime.context import close_session, get_repos

    tenant_a = f"tenant_evc_iso_a_{uuid4().hex[:6]}"
    tenant_b = f"tenant_evc_iso_b_{uuid4().hex[:6]}"
    key_a = "key_evc_iso_a"
    key_b = "key_evc_iso_b"
    graph_id = f"graph_evc_iso_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'evc_iso.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"],"{tenant_b}":["{key_b}"]}}',
        database_url=database_url,
    )

    repos = get_repos(tenant_a)
    session = repos["session"]
    try:
        _seed_graph(session, tenant_a, graph_id)
    finally:
        close_session(session)

    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}
    headers_b = {"X-Tenant-Id": tenant_b, "X-Api-Key": key_b}

    body_a = client.get(
        f"/api/v1/evolve/invention/flow?graph_id={graph_id}",
        headers=headers_a,
    ).json()
    assert body_a["tenant_id"] == tenant_a
    assert body_a["node_count"] >= 3

    body_b = client.get(
        f"/api/v1/evolve/invention/flow?graph_id={graph_id}",
        headers=headers_b,
    ).json()
    assert body_b["tenant_id"] == tenant_b
    assert body_b["node_count"] == 0
    assert body_b["stages"]["atoms"] == []
