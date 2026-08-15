"""Phase EV-E acceptance: evolution backup & restore (safe undo).

Coverage:
- Pre-action backups are written before prune deletions during /evolve.
- Version history reports backup_count per cycle.
- GET /evolve/backups lists snapshots (tenant-isolated).
- POST /evolve/backups/restore re-inserts nodes idempotently.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import jwt
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


def _seed_redundant_graph(session, tenant_id: str, graph_id: str) -> int:
    """Seed rich atoms that evolution can safely prune."""
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

    engine = FAIMNativeEngine(
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        graph_version_repo=gv_repo,
    )

    for i in range(5):
        # Near-duplicate content so the cycle has heavy redundancy to prune.
        text = (
            f"Kubernetes pod scheduling schedules containers {i} with "
            "resource requests and limits, replicas, services"
        )
        raw = route_extraction(text.encode("utf-8"), f"raw-{i}.txt", f"raw-{i}")
        vectors = vectorize_blocks(raw)
        engine.write_atoms(graph_id=graph_id, vectors=vectors)
    session.commit()
    return len(node_repo.list_atoms(graph_id=graph_id, limit=100))


def _run_evolve_with_permissive_policy(
    session, tenant_id: str, graph_id: str
) -> dict:
    """Run evolve_once directly with a permissive prune policy.

    The API defaults never prune on small graphs (7-day age gate + merge-first
    ordering), so the test drives the core directly to deterministically
    exercise the backup-before-prune path.
    """
    from core.dynamics.evolution_native import evolve_once
    from core.operators.prune import PrunePolicy
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo

    node_repo = NodeRepo(session, tenant_id=tenant_id)
    edge_repo = EdgeRepo(session, tenant_id=tenant_id)
    event_repo = EventRepo(tenant_id=tenant_id)
    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)

    result = evolve_once(
        graph_id=graph_id,
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        graph_version_repo=gv_repo,
        max_actions=25,
        prune_policy=PrunePolicy(
            min_age_days=0.0,
            max_touch_count=5,
            min_similarity_for_redundancy=0.5,
        ),
    )
    session.commit()
    return {
        "merges": result.merges,
        "prunes": result.prunes,
        "inventions": result.inventions,
    }


def test_phase_ev_e_backup_restore_roundtrip(monkeypatch, tmp_path):
    from runtime.context import close_session, get_repos

    tenant_a = f"tenant_eve_a_{uuid4().hex[:6]}"
    key_a = "key_eve_a"
    graph_id = f"graph_eve_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'eve_backup.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"]}}',
        database_url=database_url,
    )

    repos = get_repos(tenant_a)
    session = repos["session"]
    try:
        atom_count = _seed_redundant_graph(session, tenant_a, graph_id)
        outcome = _run_evolve_with_permissive_policy(session, tenant_a, graph_id)
    finally:
        close_session(session)
    assert atom_count >= 4

    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}

    # The cycle must have pruned nodes — each protected by a pre-action backup.
    pruned = int(outcome.get("prunes", 0) or 0)
    assert pruned >= 1, outcome

    # Every prune must be protected by a pre-action backup.
    backups_resp = client.get(
        f"/api/v1/evolve/backups?graph_id={graph_id}",
        headers=headers_a,
    )
    assert backups_resp.status_code == 200
    backups_body = backups_resp.json()
    assert backups_body["count"] == pruned
    assert all(item["action_type"] == "prune" for item in backups_body["items"])
    pruned_node_ids = {item["node_id"] for item in backups_body["items"]}
    assert len(pruned_node_ids) == pruned

    # Version history exposes the backups for that cycle.
    versions_resp = client.get(
        f"/api/v1/evolve/invention/versions?graph_id={graph_id}",
        headers=headers_a,
    )
    assert versions_resp.status_code == 200
    rows = versions_resp.json()["versions"]
    latest = max(rows, key=lambda r: r["version"])
    assert latest["prunes"] == pruned
    assert latest["backup_count"] == pruned

    # Restore roundtrip: all pruned nodes come back with their identity.
    restore_resp = client.post(
        "/api/v1/evolve/backups/restore",
        headers=headers_a,
        json={"graph_id": graph_id, "version": latest["version"]},
    )
    assert restore_resp.status_code == 200
    restore_body = restore_resp.json()
    assert restore_body["restored"] == pruned
    assert restore_body["skipped"] == 0
    assert set(restore_body["node_ids"]) == pruned_node_ids

    repos = get_repos(tenant_a)
    session = repos["session"]
    try:
        from store.pg.repos.node_repo import NodeRepo

        node_repo = NodeRepo(session, tenant_id=tenant_a)
        restored_ids = {
            str(n.node_id) for n in node_repo.list_atoms(graph_id=graph_id, limit=100)
        }
    finally:
        close_session(session)
    assert pruned_node_ids <= restored_ids

    # Idempotency: a second restore skips everything.
    restore2 = client.post(
        "/api/v1/evolve/backups/restore",
        headers=headers_a,
        json={"graph_id": graph_id, "version": latest["version"]},
    )
    assert restore2.status_code == 200
    body2 = restore2.json()
    assert body2["restored"] == 0
    assert body2["skipped"] == pruned


def test_phase_ev_e_backups_tenant_isolation(monkeypatch, tmp_path):
    from runtime.context import close_session, get_repos

    tenant_a = f"tenant_eve_b_{uuid4().hex[:6]}"
    key_a = "key_eve_b"
    tenant_b = f"tenant_eve_c_{uuid4().hex[:6]}"
    key_b = "key_eve_c"
    graph_a = f"graph_eve_b_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'eve_iso.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=(
            f'{{"{tenant_a}":["{key_a}"],"{tenant_b}":["{key_b}"]}}'
        ),
        database_url=database_url,
    )

    repos = get_repos(tenant_a)
    session = repos["session"]
    try:
        _seed_redundant_graph(session, tenant_a, graph_a)
        outcome = _run_evolve_with_permissive_policy(session, tenant_a, graph_a)
    finally:
        close_session(session)
    assert int(outcome.get("prunes", 0) or 0) >= 1

    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}
    headers_b = {"X-Tenant-Id": tenant_b, "X-Api-Key": key_b}

    own = client.get(
        f"/api/v1/evolve/backups?graph_id={graph_a}", headers=headers_a
    )
    other = client.get(
        f"/api/v1/evolve/backups?graph_id={graph_a}", headers=headers_b
    )
    assert own.status_code == 200
    assert other.status_code == 200
    assert own.json()["count"] >= 1
    assert other.json()["count"] == 0


def test_phase_ev_e_restore_unknown_graph_is_empty(monkeypatch, tmp_path):
    tenant_a = f"tenant_eve_d_{uuid4().hex[:6]}"
    key_a = "key_eve_d"
    graph_id = f"graph_eve_d_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'eve_empty.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"]}}',
        database_url=database_url,
    )
    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}

    resp = client.post(
        "/api/v1/evolve/backups/restore",
        headers=headers_a,
        json={"graph_id": graph_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["restored"] == 0
    assert body["skipped"] == 0


def test_phase_ev_e_metrics_surface(monkeypatch, tmp_path):
    """Scrapeable evolution health: cycles, data safety, learning, alerts."""
    from runtime.context import close_session, get_repos

    tenant_a = f"tenant_eve_f_{uuid4().hex[:6]}"
    key_a = "key_eve_f"
    graph_id = f"graph_eve_f_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'eve_metrics.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"]}}',
        database_url=database_url,
    )

    repos = get_repos(tenant_a)
    session = repos["session"]
    try:
        _seed_redundant_graph(session, tenant_a, graph_id)
        outcome = _run_evolve_with_permissive_policy(session, tenant_a, graph_id)
    finally:
        close_session(session)
    assert int(outcome.get("prunes", 0) or 0) >= 1

    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}
    resp = client.get(f"/api/v1/evolve/metrics?graph_id={graph_id}", headers=headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["graph_id"] == graph_id
    assert body["tenant_id"] == tenant_a

    # Cycles + data safety from the journal + backup journal.
    assert body["cycles"]["count"] == 1
    assert body["cycles"]["last_prunes"] == int(outcome["prunes"])
    assert body["data_safety"]["backups_available"] == int(outcome["prunes"])
    assert body["data_safety"]["coverage_ok"] is True
    assert body["data_safety"]["latest_cycle_backups"] == int(outcome["prunes"])

    # No critical alerts when coverage is intact.
    codes = [a["code"] for a in body["alerts"]]
    assert "backup_coverage_gap" not in codes

    # Learning block is always present and structured.
    assert body["learning"]["outcomes_count"] >= 0
    assert "policy_version" in body["learning"]
    assert "trust_ready" in body["learning"]
    assert "reward_trend_slope" in body["learning"]


def test_phase_ev_e_metrics_cold_graph_has_waiting_alert(monkeypatch, tmp_path):
    tenant_a = f"tenant_eve_g_{uuid4().hex[:6]}"
    key_a = "key_eve_g"
    graph_id = f"graph_eve_g_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'eve_metrics_cold.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"]}}',
        database_url=database_url,
    )
    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}

    resp = client.get(f"/api/v1/evolve/metrics?graph_id={graph_id}", headers=headers_a)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cycles"]["count"] == 0
    assert body["alerts"]
    codes = {a["code"] for a in body["alerts"]}
    assert "no_cycles_recorded" in codes