"""Unit tests for graph-scoped canonical semantics repository."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.store.pg.models_faim import Base
from faim_native.store.pg.repos.canonical_semantics_repo import CanonicalSemanticsRepo


def test_canonical_semantics_repo_roundtrip():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        repo = CanonicalSemanticsRepo(session=session, tenant_id="tenant_can_repo")
        graph_id = f"graph-{uuid4().hex[:8]}"

        repo.replace_term_stats(
            graph_id,
            [
                {
                    "channel": "term",
                    "term": "revenue",
                    "df": 2,
                    "cf": 3,
                    "doc_count": 3,
                    "context_terms": {"sales": 2},
                }
            ],
        )
        repo.replace_lexicon(
            graph_id,
            [
                {
                    "surface_form": "rcp",
                    "canonical_form": "retrieval control plane",
                    "kind": "acronym",
                    "support_count": 1,
                    "score": 0.7,
                    "meta": {"support_count": 1},
                }
            ],
        )

        stats = repo.list_term_stats(graph_id)
        lexicon = repo.list_lexicon_entries(graph_id)
        canonical_map = repo.get_canonical_map(graph_id)

        assert len(stats) == 1
        assert len(lexicon) == 1
        assert canonical_map["rcp"] == ("retrieval control plane",)
    finally:
        session.close()
