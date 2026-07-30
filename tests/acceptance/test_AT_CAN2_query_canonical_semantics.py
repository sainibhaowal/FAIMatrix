"""Acceptance test for query-time canonical semantics expansion."""

from __future__ import annotations

from uuid import uuid4


def _configure_isolated_runtime(
    monkeypatch, tmp_path, tenant_id: str, api_key: str
) -> str:
    db_url = f"sqlite:///{tmp_path / ('faim_can_query_' + uuid4().hex + '.db')}"

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


def _ingest_payload(
    repos, tenant_id: str, graph_id: str, filename: str, payload: bytes
):
    from core.engine_native import FAIMNativeEngine
    from encoding.text_vectorizer import vectorize_blocks
    from perception.router import route_extraction
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo

    session = repos["session"]
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
    write_result = engine.write_atoms(graph_id=graph_id, vectors=vectors, reprs_v2=None)
    repos["storage_file_repo"].mark_ingest_result(
        session,
        raw_id=saved.id,
        graph_id=graph_id,
        status="completed",
        packet_hash=f"packet-{filename}",
        node_count=write_result.nodes_written,
        vector_count=len(vectors),
        error_message=None,
        job_id=None,
    )
    session.commit()
    return saved.id


def test_query_uses_canonical_semantics_alias_expansion(monkeypatch, tmp_path):
    from lexical.canonicalizer import canonicalize_text
    from orchestration.canonical_semantics_rebuild import (
        run_canonical_semantics_rebuild,
    )
    from orchestration.ingest_flow import FAIMProfile
    from orchestration.query_flow import run_query
    from runtime.context import close_session, get_repos
    from store.pg.repos.canonical_semantics_repo import CanonicalSemanticsRepo

    tenant_id = "tenant_can_query"
    api_key = "canonical_query_key"
    graph_id = f"graph-can-query-{uuid4().hex[:8]}"

    _configure_isolated_runtime(monkeypatch, tmp_path, tenant_id, api_key)

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        raw_id = _ingest_payload(
            repos,
            tenant_id,
            graph_id,
            "query-1.txt",
            b"Retrieval Control Plane (RCP) manages queue orchestration latency.",
        )
        _ingest_payload(
            repos,
            tenant_id,
            graph_id,
            "query-2.txt",
            b"Budget planning and revenue review continue this quarter.",
        )

        rebuild = run_canonical_semantics_rebuild(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            raw_repo=repos["raw_repo"],
            storage_file_repo=repos["storage_file_repo"],
            raw_store=repos["raw_store"],
            node_repo=repos["node_repo"],
            edge_repo=repos["edge_repo"],
            gv_repo=repos["gv_repo"],
            event_repo=repos["event_repo"],
        )
        session.commit()

        assert rebuild.lexicon_written >= 1
        repo = CanonicalSemanticsRepo(session=session, tenant_id=tenant_id)
        canonical_map = repo.get_canonical_map(graph_id)
        canonical = canonicalize_text("rcp latency", canonical_map=canonical_map)
        assert "retrieval control plane" in canonical.canonical_text

        result = run_query(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            query_text="rcp latency",
            k=3,
            profile=FAIMProfile.STRICT,
            return_explain=True,
        )
        assert result.results
        top = result.results[0]
        assert top["evidence"]["raw_id"] == str(raw_id)
        assert "phaseB_query_expansion" in top["explain"]
        phase_b = top["explain"]["phaseB_query_expansion"]
        assert "retrieval control plane" in phase_b["expanded_query_text"]
        assert phase_b["source_counts"].get("canonical_lemma", 0) >= 1
    finally:
        close_session(session)
