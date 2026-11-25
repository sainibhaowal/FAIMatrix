"""Unit tests for dynamic FAIM-Pure vs ML embedding routing and CPU safety."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from encoding.embedding_providers import (
    EmbeddingResult,
    is_english_text,
    should_use_ml_embedding,
)
from orchestration.ingest_flow import FAIMProfile, run_ingest
from orchestration.query_flow import run_query
from store.pg.models_faim import Base, NodeModel
from store.pg.repos.edge_repo import EdgeRepo
from store.pg.repos.event_repo import EventRepo
from store.pg.repos.graph_version_repo import GraphVersionRepo
from store.pg.repos.node_repo import NodeRepo


def test_is_english_text_detects_english_and_multilingual_inputs():
    assert is_english_text("Quarterly revenue report for Q4 operations.") is True
    assert is_english_text("") is True

    assert is_english_text("Umsatz Quartal Bericht fuer das Unternehmen.") is False
    assert is_english_text("Revenus du trimestre pour l'entreprise.") is False
    assert is_english_text("Ingresos del trimestre financiero.") is False
    assert is_english_text("東京の天気予報を教えてください") is False
    assert is_english_text("मेरा नाम क्या है") is False
    assert is_english_text("ما هو تقرير الأرباح") is False


def test_should_use_ml_embedding_dynamic_routing(monkeypatch):
    monkeypatch.setenv("FAIM_FAST_ML_EMBEDDING", "auto")

    # Regular modes ALWAYS use the active embedding model regardless of language
    assert should_use_ml_embedding("Quarterly revenue report", is_fast_mode=False) == (
        True,
        "regular_embedding",
    )
    assert should_use_ml_embedding("Umsatz Quartal Bericht", is_fast_mode=False) == (
        True,
        "regular_embedding",
    )

    # FAST mode routes dynamically by language
    assert should_use_ml_embedding("Quarterly revenue report", is_fast_mode=True) == (
        False,
        "fast_pure_english",
    )
    assert should_use_ml_embedding("Umsatz Quartal Bericht", is_fast_mode=True) == (
        True,
        "fast_multilingual_embedding",
    )
    assert should_use_ml_embedding(
        ["Quarterly revenue report", "Umsatz Quartal Bericht"],
        is_fast_mode=True,
    ) == (True, "fast_multilingual_embedding")


def test_should_use_ml_embedding_honors_explicit_overrides(monkeypatch):
    monkeypatch.setenv("FAIM_FAST_ML_EMBEDDING", "false")
    assert should_use_ml_embedding("Umsatz Quartal", is_fast_mode=True) == (
        False,
        "fast_pure_forced",
    )
    assert should_use_ml_embedding("Quarterly revenue", is_fast_mode=False) == (
        True,
        "regular_embedding",
    )

    monkeypatch.setenv("FAIM_FAST_ML_EMBEDDING", "true")
    assert should_use_ml_embedding("Quarterly revenue", is_fast_mode=True) == (
        True,
        "ml_embedding_forced",
    )


def test_run_query_routes_english_fast_to_pure_and_regular_or_multilingual_to_embeddings(
    monkeypatch,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    calls = []

    class _DummyProvider:
        def is_available(self) -> bool:
            return True

        def encode_single(self, text: str):
            calls.append(text)
            return [0.1] * 8

        @property
        def model_info(self):
            return SimpleNamespace(name="dummy-cpu", dimension=8)

    monkeypatch.setenv("FAIM_FAST_ML_EMBEDDING", "auto")
    monkeypatch.setenv("FAIM_REPR_V2_ENABLED", "true")
    monkeypatch.setenv("FAIM_FAST_RELEVANCE_FIRST", "true")

    try:
        with patch(
            "encoding.get_active_embedding_provider", return_value=_DummyProvider()
        ):
            # 1) FAST + English -> FAIM-Pure (provider must NOT be invoked)
            res_fast_en = run_query(
                session=session,
                tenant_id="t1",
                graph_id="g1",
                query_text="Quarterly revenue report",
                profile=FAIMProfile.FAST,
            )
            assert res_fast_en.metrics["ml_embedding_used"] == 0.0
            assert len(calls) == 0

            # 2) FAST + Non-English -> ML embedding runs dynamically
            res_fast_de = run_query(
                session=session,
                tenant_id="t1",
                graph_id="g1",
                query_text="Umsatz Quartal Bericht",
                profile=FAIMProfile.FAST,
            )
            assert res_fast_de.metrics["ml_embedding_used"] == 1.0
            assert len(calls) == 1

            # 3) Regular mode (STRICT) + English -> ML embedding ALWAYS runs
            res_strict_en = run_query(
                session=session,
                tenant_id="t1",
                graph_id="g1",
                query_text="Quarterly revenue report",
                profile=FAIMProfile.STRICT,
            )
            assert res_strict_en.metrics["ml_embedding_used"] == 1.0
            assert len(calls) == 2
    finally:
        session.close()


def test_run_ingest_routes_english_fast_to_pure_and_regular_or_multilingual_to_embeddings(
    monkeypatch,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    encode_calls = []

    class _DummyIngestProvider:
        def is_available(self) -> bool:
            return True

        def encode(self, texts):
            encode_calls.append(list(texts))
            return EmbeddingResult(
                vectors=[[0.25] * 8 for _ in texts],
                dimension=8,
                model_name="dummy-cpu",
                token_count=sum(len(t.split()) for t in texts),
            )

        @property
        def model_info(self):
            return SimpleNamespace(name="dummy-cpu", dimension=8)

    monkeypatch.setenv("FAIM_FAST_ML_EMBEDDING", "auto")
    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")
    monkeypatch.setenv("FAIM_ENABLE_INDEX", "false")

    repo_kwargs = {
        "node_repo": NodeRepo(session=session, tenant_id="t1"),
        "edge_repo": EdgeRepo(session=session, tenant_id="t1"),
        "event_repo": EventRepo(session=session, tenant_id="t1"),
        "gv_repo": GraphVersionRepo(tenant_id="t1"),
    }

    try:
        with patch(
            "encoding.get_active_embedding_provider",
            return_value=_DummyIngestProvider(),
        ):
            # 1) FAST + English -> FAIM-Pure (provider encode must NOT be called)
            r1 = run_ingest(
                graph_id="g_dyn",
                raw_id="raw_en_fast",
                filename="en_fast.txt",
                file_bytes=b"Quarterly revenue growth remained steady across core English markets.",
                tenant_id="t1",
                session=session,
                profile=FAIMProfile.FAST,
                **repo_kwargs,
            )
            assert r1.status == "completed"
            assert len(encode_calls) == 0

            # 2) FAST + Non-English -> ML embedding runs dynamically
            r2 = run_ingest(
                graph_id="g_dyn",
                raw_id="raw_de_fast",
                filename="de_fast.txt",
                file_bytes="Umsatz und Quartal Bericht fuer das Unternehmen im dritten Monat.".encode(
                    "utf-8"
                ),
                tenant_id="t1",
                session=session,
                profile=FAIMProfile.FAST,
                **repo_kwargs,
            )
            assert r2.status == "completed"
            assert len(encode_calls) == 1

            # 3) Regular mode (STRICT) + English -> ML embedding ALWAYS runs
            r3 = run_ingest(
                graph_id="g_dyn",
                raw_id="raw_en_strict",
                filename="en_strict.txt",
                file_bytes=b"Annual infrastructure resilience report and recovery objectives.",
                tenant_id="t1",
                session=session,
                profile=FAIMProfile.STRICT,
                **repo_kwargs,
            )
            assert r3.status == "completed"
            assert len(encode_calls) == 2

        nodes = (
            session.query(NodeModel)
            .filter(NodeModel.tenant_id == "t1", NodeModel.graph_id == "g_dyn")
            .all()
        )
        assert len(nodes) >= 3
        by_raw = {n.raw_id: n for n in nodes}
        assert by_raw["raw_en_fast"].v_embedding is None
        assert by_raw["raw_de_fast"].v_embedding == [0.25] * 8
        assert by_raw["raw_en_strict"].v_embedding == [0.25] * 8
    finally:
        session.close()
