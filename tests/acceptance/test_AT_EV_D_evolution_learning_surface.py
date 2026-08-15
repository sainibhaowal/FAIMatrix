"""Phase EV-D acceptance: evolution learning API surface.

GET /api/v1/evolve/learning/{state,outcomes,meta} return real persisted
learning rows with tenant isolation, read-only behavior, and feature-flag
gating — never mutating on read.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient


def _mk_client(
    monkeypatch, *, tenant_keys_json: str, database_url: str, learning_enabled: bool
) -> TestClient:
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
    monkeypatch.setenv(
        "FAIM_EVOLUTION_LEARNING_ENABLED", "true" if learning_enabled else "false"
    )
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


def test_phase_ev_d_learning_routes_present():
    from api.routers.evolve import router

    paths = {route.path for route in router.routes}
    assert "/evolve/learning/state" in paths
    assert "/evolve/learning/outcomes" in paths
    assert "/evolve/learning/meta" in paths


def _seed_learning(session, tenant_id: str, graph_id: str) -> None:
    """Seed one outcome + one meta-metric + one policy state row."""
    from core.learning.evolution_policy import (
        EvolutionPolicy,
        KNOB_GRIDS,
    )
    from store.pg.repos.evolution_learning_repo import (
        EvolutionLearningRepo,
        EvolutionOutcome,
        MetaMetricSnapshot,
    )

    repo = EvolutionLearningRepo(session=session, tenant_id=tenant_id)
    repo.record_outcome(
        graph_id,
        EvolutionOutcome(
            graph_version=7,
            merges=3,
            prunes=1,
            inventions=1,
            theories=0,
            lambda_before=0.31,
            lambda_after=0.27,
            r_before=0.5,
            r_after=0.12,
            n_before=0.2,
            n_after=0.33,
            d_before=0.4,
            d_after=0.36,
            h_before=0.5,
            h_after=0.41,
            e_before=0.4,
            e_after=0.42,
            retrieval_delta=0.14,
            reward=0.82,
            policy_snapshot={"merge_threshold": "0.90"},
        ),
    )
    repo.record_meta_metrics(
        graph_id,
        MetaMetricSnapshot(
            merge_usefulness=0.9,
            invention_utilization=0.6,
            prune_regret=0.05,
            d_drift=0.01,
            h_drift=0.02,
            alerts={"level": "ok"},
        ),
    )
    policy = EvolutionPolicy(graph_id=graph_id, seed=1)
    arms = {knob: arm.to_dict() for knob, arm in policy.arms.items()}
    for value in KNOB_GRIDS["merge_threshold"]:
        policy.update_from_outcome(
            _Outcome(merge_threshold=value),
            merges=1,
            prunes=0,
            r_before=0.5,
            r_after=0.3,
            n_before=0.1,
            n_after=0.2,
            e_before=0.5,
            e_after=0.4,
            lambda_after=0.30,
            context={"R": 0.5, "N": 0.5, "D": 1.5, "H": 0.5, "node_count": 100},
        )
    state = policy.to_state()
    repo.save_policy_state(
        graph_id,
        arms=state["arms"],
        lambda_calibration=state["lambda_calibration"],
        meta={"last_cycle": "seeded"},
        policy_version=state["version"],
    )
    session.commit()


class _Outcome:
    """Lightweight knob carrier for policy.update_from_outcome."""

    def __init__(self, merge_threshold: float):
        self.merge_threshold = merge_threshold
        self.prune_similarity_threshold = 0.90
        self.prune_min_age_days = 1
        self.lambda_threshold = 0.30


def test_phase_ev_d_learning_defaults_read_only(monkeypatch, tmp_path):
    from runtime.context import close_session, get_repos

    tenant = f"tenant_evd_dflt_{uuid4().hex[:6]}"
    key = "key_evd_dflt"
    graph_id = f"graph_evd_dflt_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'evd_defaults.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant}":["{key}"]}}',
        database_url=database_url,
        learning_enabled=False,
    )
    headers = {"X-Tenant-Id": tenant, "X-Api-Key": key}

    state = client.get(
        f"/api/v1/evolve/learning/state?graph_id={graph_id}", headers=headers
    ).json()
    assert state["enabled"] is False
    assert state["schema_tag"] == "v2"
    assert state["policy_version"] == 0
    assert state["source"] == "defaults"
    assert state["learned"] is False
    assert state["knobs"]["merge_threshold"] == 0.95
    assert state["calibration"]["n"] == 0
    assert all(not s["visits"] for s in state["samples"].values())

    outcomes = client.get(
        f"/api/v1/evolve/learning/outcomes?graph_id={graph_id}", headers=headers
    ).json()
    assert outcomes["enabled"] is False
    assert outcomes["total"] == 0
    assert outcomes["outcomes"] == []

    meta = client.get(
        f"/api/v1/evolve/learning/meta?graph_id={graph_id}", headers=headers
    ).json()
    assert meta["enabled"] is False
    assert meta["total"] == 0
    assert meta["meta_metrics"] == []

    again = client.get(
        f"/api/v1/evolve/learning/state?graph_id={graph_id}", headers=headers
    ).json()
    assert again == state  # reads never mutate


def test_phase_ev_d_learning_seeded_state(monkeypatch, tmp_path):
    from runtime.context import close_session, get_repos

    tenant = f"tenant_evd_seed_{uuid4().hex[:6]}"
    key = "key_evd_seed"
    graph_id = f"graph_evd_seed_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'evd_seed.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant}":["{key}"]}}',
        database_url=database_url,
        learning_enabled=True,
    )
    repos = get_repos(tenant)
    session = repos["session"]
    try:
        _seed_learning(session, tenant, graph_id)
    finally:
        close_session(session)

    headers = {"X-Tenant-Id": tenant, "X-Api-Key": key}

    state = client.get(
        f"/api/v1/evolve/learning/state?graph_id={graph_id}", headers=headers
    ).json()
    assert state["enabled"] is True
    assert state["schema_tag"] == "v2"
    assert state["policy_version"] >= 1
    assert state["learned"] is True
    assert state["source"] == "bandit"
    assert len(state["samples"]["merge_threshold"]["visits"]) >= 1
    assert state["calibration"]["n"] >= 1

    outcomes = client.get(
        f"/api/v1/evolve/learning/outcomes?graph_id={graph_id}", headers=headers
    ).json()
    assert outcomes["enabled"] is True
    assert outcomes["total"] == 1
    row = outcomes["outcomes"][0]
    assert row["merges"] == 3
    assert row["prunes"] == 1
    assert row["reward"] == 0.82
    assert row["retrieval_delta"] == 0.14

    meta = client.get(
        f"/api/v1/evolve/learning/meta?graph_id={graph_id}", headers=headers
    ).json()
    assert meta["enabled"] is True
    assert meta["total"] == 1
    metric = meta["meta_metrics"][0]
    assert metric["merge_usefulness"] == 0.9
    assert metric["invention_utilization"] == 0.6
    assert metric["prune_regret"] == 0.05


def test_phase_ev_d_learning_tenant_isolation(monkeypatch, tmp_path):
    from runtime.context import close_session, get_repos

    tenant_a = f"tenant_evd_iso_a_{uuid4().hex[:6]}"
    tenant_b = f"tenant_evd_iso_b_{uuid4().hex[:6]}"
    key_a = "key_evd_iso_a"
    key_b = "key_evd_iso_b"
    graph_id = f"graph_evd_iso_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'evd_iso.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"],"{tenant_b}":["{key_b}"]}}',
        database_url=database_url,
        learning_enabled=True,
    )
    repos = get_repos(tenant_a)
    session = repos["session"]
    try:
        _seed_learning(session, tenant_a, graph_id)
    finally:
        close_session(session)

    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}
    headers_b = {"X-Tenant-Id": tenant_b, "X-Api-Key": key_b}

    body_a = client.get(
        f"/api/v1/evolve/learning/outcomes?graph_id={graph_id}", headers=headers_a
    ).json()
    assert body_a["total"] == 1

    body_b = client.get(
        f"/api/v1/evolve/learning/outcomes?graph_id={graph_id}", headers=headers_b
    ).json()
    assert body_b["total"] == 0
    assert body_b["outcomes"] == []

    state_b = client.get(
        f"/api/v1/evolve/learning/state?graph_id={graph_id}", headers=headers_b
    ).json()
    assert state_b["policy_version"] == 0
    assert all(not s["visits"] for s in state_b["samples"].values())
