"""Phase EV-F acceptance: self-evolution theory generation.

Theory generation is a bounded, deterministic, λ-gated pass run inside the
self-evolution loop. It derives symbolic generalizations from observed graph
structure (cross-galaxy correlations, redundancy clusters, hierarchy
composition, cognitive-type mix), persists them durably, and surfaces them
through the evolve API.

This suite verifies:
1. The `/api/v1/evolve/theories` route exists.
2. `run_theory_cycle` produces bounded, idempotent theories with evidence.
3. Theories persist durably and can be re-listed after a new repo instance.
4. Low λ gates theory generation (no theories without evolution pressure).
5. Cross-galaxy nodes sharing a concept yield a correlation theory.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

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


def _seed_graph(session, tenant_id: str, graph_id: str) -> None:
    """Seed nodes with cross-galaxy structure and cognitive types."""
    import hashlib

    from encoding.vector_schema import FAIMVector, VECTOR_DIMENSION
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.repos.representation_repo import RepresentationRepo

    node_repo = NodeRepo(session, tenant_id=tenant_id)
    repr_repo = RepresentationRepo(session=session, tenant_id=tenant_id)

    def _vector(text: str, seed: int) -> FAIMVector:
        v = [0.0] * VECTOR_DIMENSION
        h = hashlib.sha256(f"{seed}:{text}".encode()).digest()
        for i in range(min(VECTOR_DIMENSION, len(h))):
            v[i] = (h[i] / 255.0) * 2.0 - 1.0
        from core.contracts.types import BlockAnchor

        anchor = BlockAnchor(doc_type="text", section=f"sec-{seed}")
        return FAIMVector.create(
            raw_id=f"raw-{seed}",
            block_id=f"block-{seed}",
            block_type="text",
            anchor=anchor,
            v_native=v,
            opp_signature={"norm": 1.0, "density": 1.0},
        )

    def _write(text: str, galaxy: str, cog_type: str, seed: int) -> str:
        from encoding.representation_v2 import build_representation_v2

        vec = _vector(text, seed)
        node_id = node_repo.upsert_atom_node(
            graph_id=graph_id,
            vector=vec,
            cognitive_type=cog_type,
            galaxy_id=galaxy,
        )
        repr_repo.upsert_node_representation(
            graph_id=graph_id,
            node_id=node_id,
            representation=build_representation_v2(
                text, display_text=text
            ),
        )
        return str(node_id)

    # Two galaxies share the concept "Atlas" → correlation theory.
    _write(
        "Atlas leads the European mission control", "galaxy-alpha", "fact", 1
    )
    _write(
        "Atlas coordinates rescue across the border", "galaxy-beta", "fact", 2
    )
    # Same cognitive type dominance → composition theory.
    _write("Atlas tracks orbital debris", "galaxy-alpha", "fact", 3)
    _write("Solar panels degrade slowly in orbit", "galaxy-alpha", "fact", 4)
    # A macro node exists → hierarchy theory.
    atoms = node_repo.list_atoms(graph_id=graph_id, limit=10)
    if len(atoms) >= 2:
        from core.dynamics.invention_native import invent_macro
        from store.pg.repos.edge_repo import EdgeRepo
        from store.pg.repos.event_repo import EventRepo

        edge_repo = EdgeRepo(session, tenant_id=tenant_id)
        event_repo = EventRepo(tenant_id=tenant_id)
        invent_macro(
            graph_id=graph_id,
            member_ids=[atoms[0].node_id, atoms[1].node_id],
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            skip_lambda_check=True,
            coactivation_count=4,
        )
    session.commit()


def test_phase_ev_f_theories_route_present():
    from api.routers.evolve import router

    paths = {route.path for route in router.routes}
    assert "/evolve/theories" in paths


def test_run_theory_cycle_bounded_idempotent(monkeypatch, tmp_path):
    """Theories are bounded, stable ids, and persist durably."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core.dynamics.theory_native import run_theory_cycle
    from store.pg.models_faim import Base
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.repos.theory_repo import TheoryRepo

    tenant_id = f"tenant_evf_{uuid4().hex[:6]}"
    graph_id = f"graph_evf_{uuid4().hex[:8]}"
    db_url = f"sqlite:///{tmp_path}/faim_evf_{uuid4().hex}.db"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        _seed_graph(session, tenant_id, graph_id)
        node_repo = NodeRepo(session, tenant_id=tenant_id)

        # High λ → theories generated, bounded to max_theories.
        res1 = run_theory_cycle(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            theory_repo=TheoryRepo(session, tenant_id),
            graph_version=3,
            lambda_hat=0.75,
            lambda_threshold=0.3,
            max_theories=3,
        )
        session.commit()
        assert res1.theories_created >= 1
        assert len(res1.theory_ids) == res1.theories_created
        assert len(res1.theory_ids) <= 3

        # Re-run: same ids (idempotent), durable rows not duplicated.
        res2 = run_theory_cycle(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            theory_repo=TheoryRepo(session, tenant_id),
            graph_version=3,
            lambda_hat=0.75,
            lambda_threshold=0.3,
            max_theories=3,
        )
        session.commit()
        assert set(res1.theory_ids) == set(res2.theory_ids)

        # Fresh repo instance can read them back durably.
        fresh = TheoryRepo(session, tenant_id)
        rows = fresh.list_theories(graph_id)
        assert len(rows) >= 1
        assert rows[0]["graph_version"] == 3
        assert rows[0]["evidence_node_ids"]

        # Correlation theory present (Atlas in 2 galaxies).
        types = {r["theory_type"] for r in rows}
        assert "correlation" in types

        # API surface returns them with tenant isolation.
        key = "key_evf"
        client = _mk_client(
            monkeypatch,
            tenant_keys_json=f'{{"{tenant_id}":["{key}"]}}',
            database_url=db_url,
        )
        headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": key}
        resp = client.get(
            f"/api/v1/evolve/theories?graph_id={graph_id}", headers=headers
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["graph_id"] == graph_id
        assert body["total"] >= 1
        assert body["theories"][0]["description"]

        # Another tenant sees nothing.
        other = f"tenant_evf_other_{uuid4().hex[:6]}"
        other_key = "key_other"
        client2 = _mk_client(
            monkeypatch,
            tenant_keys_json=f'{{"{tenant_id}":["{key}"],"{other}":["{other_key}"]}}',
            database_url=db_url,
        )
        headers_other = {"X-Tenant-Id": other, "X-Api-Key": other_key}
        resp2 = client2.get(
            f"/api/v1/evolve/theories?graph_id={graph_id}", headers=headers_other
        )
        assert resp2.status_code == 200, resp2.text
        assert resp2.json()["total"] == 0
    finally:
        session.close()


def test_run_theory_cycle_lambda_gate(monkeypatch, tmp_path):
    """Low λ gates theory generation entirely."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core.dynamics.theory_native import run_theory_cycle
    from store.pg.models_faim import Base
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.repos.theory_repo import TheoryRepo

    tenant_id = f"tenant_evf_g_{uuid4().hex[:6]}"
    graph_id = f"graph_evf_g_{uuid4().hex[:8]}"
    db_url = f"sqlite:///{tmp_path}/faim_evf_g_{uuid4().hex}.db"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        _seed_graph(session, tenant_id, graph_id)
        node_repo = NodeRepo(session, tenant_id=tenant_id)
        res = run_theory_cycle(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            theory_repo=TheoryRepo(session, tenant_id),
            graph_version=1,
            lambda_hat=0.1,
            lambda_threshold=0.3,
            max_theories=3,
        )
        session.commit()
        assert res.theories_created == 0
        assert len(res.theory_ids) == 0
    finally:
        session.close()


def test_run_theory_cycle_empty_graph_no_theories(monkeypatch, tmp_path):
    """An empty graph produces no theories (never fabricates)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core.dynamics.theory_native import run_theory_cycle
    from store.pg.models_faim import Base
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.repos.theory_repo import TheoryRepo

    tenant_id = f"tenant_evf_e_{uuid4().hex[:6]}"
    graph_id = f"graph_evf_e_{uuid4().hex[:8]}"
    db_url = f"sqlite:///{tmp_path}/faim_evf_e_{uuid4().hex}.db"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        node_repo = NodeRepo(session, tenant_id=tenant_id)
        res = run_theory_cycle(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            theory_repo=TheoryRepo(session, tenant_id),
            graph_version=1,
            lambda_hat=0.8,
            lambda_threshold=0.3,
            max_theories=3,
        )
        session.commit()
        assert res.theories_created == 0
    finally:
        session.close()