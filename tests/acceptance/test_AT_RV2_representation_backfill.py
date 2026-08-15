"""Acceptance test for Representation V2 backfill on existing graphs."""

from __future__ import annotations

from uuid import uuid4


def _configure_isolated_runtime(
    monkeypatch, tmp_path, tenant_id: str, api_key: str
) -> str:
    db_url = f"sqlite:///{tmp_path / ('faim_rv2_backfill_' + uuid4().hex + '.db')}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("FAIM_RAW_STORE_PATH", str(tmp_path / "blobs"))
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')

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
    return db_url


def test_representation_v2_rebuild_backfills_existing_graph(monkeypatch, tmp_path):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from core.engine_native import FAIMNativeEngine
    from encoding.text_vectorizer import vectorize_blocks
    from fastapi.testclient import TestClient
    from perception.router import route_extraction
    from runtime.context import close_session, get_repos
    from store.pg.models_faim import (
        GraphRepresentationStatsModel,
        NodeRepresentationV2Model,
    )
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.repos.representation_repo import CHANNELS

    tenant_id = "tenant_rv2_backfill"
    api_key = "rv2_backfill_key"
    graph_id = f"graph-rv2-backfill-{uuid4().hex[:8]}"
    filename = "rv2-backfill.txt"
    payload = b"Berlin revenue for 2026 reached 15 percent on 2026-04-12."

    _configure_isolated_runtime(monkeypatch, tmp_path, tenant_id, api_key)
    reload_tenant_keys()

    app = create_app()
    client = TestClient(app)
    headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        raw_ref = repos["raw_store"].store(
            payload, mime_type="text/plain", graph_id=graph_id
        )
        saved = repos["raw_repo"].create(session, raw_ref)
        repos["storage_file_repo"].upsert_upload(
            session,
            graph_id=graph_id,
            raw_id=saved.id,
            filename=filename,
            mime_type="text/plain",
            size_bytes=len(payload),
            sha256=str(saved.sha256),
            job_id=None,
        )

        blocks = route_extraction(payload, filename, str(saved.id))
        vectors = vectorize_blocks(blocks)
        engine = FAIMNativeEngine(
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            event_repo=EventRepo(session=session, tenant_id=tenant_id),
            graph_version_repo=GraphVersionRepo(session=session, tenant_id=tenant_id),
        )
        write_result = engine.write_atoms(
            graph_id=graph_id, vectors=vectors, reprs_v2=None
        )

        repos["storage_file_repo"].mark_ingest_result(
            session,
            raw_id=saved.id,
            graph_id=graph_id,
            status="completed",
            packet_hash="rv2-backfill-packet",
            node_count=write_result.nodes_written,
            vector_count=len(vectors),
            error_message=None,
            job_id=None,
        )
        session.commit()

        assert (
            session.query(NodeRepresentationV2Model)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .count()
            == 0
        )
        assert (
            session.query(GraphRepresentationStatsModel)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .count()
            == 0
        )
    finally:
        close_session(session)

    response = client.post(
        f"/api/v1/storage/graphs/{graph_id}/representation-v2/rebuild",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["status"] == "ok"
    assert body["graph_id"] == graph_id
    assert body["files_scanned"] == 1
    assert body["files_loaded"] == 1
    assert body["files_failed"] == 0
    assert body["blocks_extracted"] >= 1
    assert body["matched_nodes"] >= 1
    assert body["inserted"] >= 1
    assert body["updated"] == 0
    assert body["graph_version"] >= 2
    assert body["errors"] == []

    repos_verify = get_repos(tenant_id)
    session_verify = repos_verify["session"]
    try:
        assert (
            session_verify.query(NodeRepresentationV2Model)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .count()
            >= 1
        )
        assert (
            session_verify.query(GraphRepresentationStatsModel)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .count()
            == len(CHANNELS)
        )
        latest_events = repos_verify["event_repo"].get_all(
            session_verify,
            graph_id=graph_id,
            kind="REPR_V2_BACKFILL",
            limit=10,
        )
        assert latest_events, "Expected REPR_V2_BACKFILL event"
    finally:
        close_session(session_verify)
