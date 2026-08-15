"""Phase EV-G acceptance: cross-galaxy synthesis → invention bridge.

Self-invention gains a second, synthesis-driven invention pass: the
CrossGalaxySynthesizer derives high-confidence insights whose evidence
spans multiple galaxies, and those evidence node sets become bounded,
λ-gated macro-node invention candidates.

This suite verifies:
1. `invent_from_synthesis_insights` creates macros from cross-galaxy
   insights when λ and confidence thresholds are met.
2. Insights that do not span multiple galaxies are skipped.
3. The bridge is idempotent (existing macros reused, never duplicated).
4. Low λ gates synthesis invention.
5. `run_synthesis_invention_cycle` works end-to-end against a real graph.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

import pytest  # noqa: F401


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


def _seed_cross_galaxy_graph(session, tenant_id: str, graph_id: str) -> None:
    """Seed two galaxies sharing a concept → correlation insight."""
    import hashlib

    from encoding.representation_v2 import build_representation_v2
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

    def _write(text: str, galaxy: str, seed: int) -> str:
        vec = _vector(text, seed)
        node_id = node_repo.upsert_atom_node(
            graph_id=graph_id,
            vector=vec,
            cognitive_type="fact",
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

    # Concept "Atlas" spans both galaxies → correlation insight.
    _write(
        "Atlas leads the European mission control", "galaxy-alpha", 1
    )
    _write(
        "Atlas coordinates rescue across the border", "galaxy-beta", 2
    )
    # Additional distinct content so the graph is non-trivial.
    _write("Solar panels degrade slowly in orbit", "galaxy-alpha", 3)
    _write("Quantum error correction improves throughput", "galaxy-beta", 4)
    session.commit()


def test_invent_from_synthesis_insights_cross_galaxy(monkeypatch, tmp_path):
    """A cross-galaxy insight becomes a bounded macro invention."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core.dynamics.invention_native import (
        invent_from_synthesis_insights,
    )
    from core.reasoning.cross_galaxy import CrossGalaxyInsight
    from store.pg.models_faim import Base
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.node_repo import NodeRepo

    tenant_id = f"tenant_evg_{uuid4().hex[:6]}"
    graph_id = f"graph_evg_{uuid4().hex[:8]}"
    db_url = f"sqlite:///{tmp_path}/faim_evg_{uuid4().hex}.db"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        _seed_cross_galaxy_graph(session, tenant_id, graph_id)
        node_repo = NodeRepo(session, tenant_id=tenant_id)
        edge_repo = EdgeRepo(session, tenant_id=tenant_id)
        event_repo = EventRepo(tenant_id=tenant_id)

        atoms = node_repo.list_atoms(graph_id=graph_id, limit=10)
        assert len(atoms) >= 4

        # Atlas nodes: nodes 1 & 2 in two galaxies.
        atlas_ids = [str(atoms[0].node_id), str(atoms[1].node_id)]
        insight = CrossGalaxyInsight(
            insight_id="corr_Atlas",
            insight_type="correlation",
            description="'Atlas' appears in 2 different documents",
            confidence=0.85,
            primary_galaxy="galaxy-alpha",
            supporting_galaxies=["galaxy-beta"],
            evidence_nodes=[{"node_id": nid} for nid in atlas_ids],
        )

        result = invent_from_synthesis_insights(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            insights=[insight],
            lambda_hat=0.7,
            lambda_threshold=0.3,
            max_macros=3,
            min_evidence=2,
            min_confidence=0.6,
            galaxy_count_for_cross=2,
        )
        session.commit()
        assert result.macros_created == 1
        assert len(result.macro_ids) == 1

        # Macro persisted.
        macro = node_repo.get_by_id(graph_id, result.macro_ids[0])
        assert macro is not None
        assert macro.level >= 1

        # Idempotent: re-running reuses the existing macro, no duplicate.
        result2 = invent_from_synthesis_insights(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            insights=[insight],
            lambda_hat=0.7,
            lambda_threshold=0.3,
            max_macros=3,
            min_evidence=2,
            min_confidence=0.6,
            galaxy_count_for_cross=2,
        )
        session.commit()
        assert result2.macros_created == 0
        # The existing macro is not duplicated; it remains retrievable.
        still_exists = node_repo.get_by_id(graph_id, result.macro_ids[0])
        assert still_exists is not None
    finally:
        session.close()


def test_invent_from_synthesis_insights_skips_single_galaxy(monkeypatch, tmp_path):
    """Insights not spanning multiple galaxies are skipped."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core.dynamics.invention_native import (
        invent_from_synthesis_insights,
    )
    from core.reasoning.cross_galaxy import CrossGalaxyInsight
    from store.pg.models_faim import Base
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.node_repo import NodeRepo

    tenant_id = f"tenant_evg_s_{uuid4().hex[:6]}"
    graph_id = f"graph_evg_s_{uuid4().hex[:8]}"
    db_url = f"sqlite:///{tmp_path}/faim_evg_s_{uuid4().hex}.db"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        _seed_cross_galaxy_graph(session, tenant_id, graph_id)
        node_repo = NodeRepo(session, tenant_id=tenant_id)
        edge_repo = EdgeRepo(session, tenant_id=tenant_id)
        event_repo = EventRepo(tenant_id=tenant_id)

        atoms = node_repo.list_atoms(graph_id=graph_id, limit=10)
        single_galaxy_ids = [str(atoms[0].node_id), str(atoms[2].node_id)]
        insight = CrossGalaxyInsight(
            insight_id="corr_single",
            insight_type="correlation",
            description="Single galaxy insight",
            confidence=0.9,
            primary_galaxy="galaxy-alpha",
            supporting_galaxies=[],
            evidence_nodes=[{"node_id": nid} for nid in single_galaxy_ids],
        )

        result = invent_from_synthesis_insights(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            insights=[insight],
            lambda_hat=0.7,
            lambda_threshold=0.3,
            max_macros=3,
            min_evidence=2,
            min_confidence=0.6,
            galaxy_count_for_cross=2,
        )
        session.commit()
        assert result.macros_created == 0
        assert result.skipped_candidates >= 1
    finally:
        session.close()


def test_invent_from_synthesis_insights_lambda_gate(monkeypatch, tmp_path):
    """Low λ gates synthesis invention entirely."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core.dynamics.invention_native import (
        invent_from_synthesis_insights,
    )
    from core.reasoning.cross_galaxy import CrossGalaxyInsight
    from store.pg.models_faim import Base
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.node_repo import NodeRepo

    tenant_id = f"tenant_evg_l_{uuid4().hex[:6]}"
    graph_id = f"graph_evg_l_{uuid4().hex[:8]}"
    db_url = f"sqlite:///{tmp_path}/faim_evg_l_{uuid4().hex}.db"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        _seed_cross_galaxy_graph(session, tenant_id, graph_id)
        node_repo = NodeRepo(session, tenant_id=tenant_id)
        edge_repo = EdgeRepo(session, tenant_id=tenant_id)
        event_repo = EventRepo(tenant_id=tenant_id)

        atoms = node_repo.list_atoms(graph_id=graph_id, limit=10)
        insight = CrossGalaxyInsight(
            insight_id="corr_gate",
            insight_type="correlation",
            description="'Atlas' appears in 2 different documents",
            confidence=0.85,
            primary_galaxy="galaxy-alpha",
            supporting_galaxies=["galaxy-beta"],
            evidence_nodes=[
                {"node_id": str(atoms[0].node_id)},
                {"node_id": str(atoms[1].node_id)},
            ],
        )

        result = invent_from_synthesis_insights(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            insights=[insight],
            lambda_hat=0.1,
            lambda_threshold=0.3,
            max_macros=3,
            min_evidence=2,
            min_confidence=0.6,
            galaxy_count_for_cross=2,
        )
        session.commit()
        assert result.macros_created == 0
    finally:
        session.close()


def test_run_synthesis_invention_cycle_end_to_end(monkeypatch, tmp_path):
    """run_synthesis_invention_cycle discovers galaxies and invents."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core.dynamics.invention_native import (
        run_synthesis_invention_cycle,
    )
    from store.pg.models_faim import Base
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.node_repo import NodeRepo

    tenant_id = f"tenant_evg_e_{uuid4().hex[:6]}"
    graph_id = f"graph_evg_e_{uuid4().hex[:8]}"
    db_url = f"sqlite:///{tmp_path}/faim_evg_e_{uuid4().hex}.db"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        _seed_cross_galaxy_graph(session, tenant_id, graph_id)
        node_repo = NodeRepo(session, tenant_id=tenant_id)
        edge_repo = EdgeRepo(session, tenant_id=tenant_id)
        event_repo = EventRepo(tenant_id=tenant_id)

        result = run_synthesis_invention_cycle(
            graph_id=graph_id,
            session=session,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            lambda_hat=0.8,
            lambda_threshold=0.3,
            max_macros=3,
        )
        session.commit()
        # Atlas correlation spans 2 galaxies → at least one macro.
        assert result.macros_created >= 1
        assert len(result.macro_ids) == result.macros_created
    finally:
        session.close()