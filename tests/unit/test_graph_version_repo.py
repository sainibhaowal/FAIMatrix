"""Unit tests for GraphVersionRepo atomic PostgreSQL upserts and fallback."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker

from faim_native.store.pg.models_faim import Base
from faim_native.store.pg.repos.graph_version_repo import (
    GraphVersionModel,
    GraphVersionRepo,
)


def _make_pg_mock_session(scalar_value: int = 1) -> MagicMock:
    session = MagicMock()
    session.get_bind.return_value = SimpleNamespace(
        dialect=SimpleNamespace(name="postgresql")
    )
    session.identity_map = {}
    session.execute.return_value.scalar_one.return_value = scalar_value
    return session


def test_bump_uses_postgresql_on_conflict_upsert() -> None:
    """PostgreSQL bump() emits atomic INSERT ... ON CONFLICT DO UPDATE."""
    session = _make_pg_mock_session(scalar_value=3)
    cached = GraphVersionModel(tenant_id="t1", graph_id="g1", version=2, reason="old")
    session.identity_map = {("g1",): cached}

    repo = GraphVersionRepo(session=session, tenant_id="t1")
    ver = repo.bump(session, "g1", "ingest")

    assert ver == 3
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    compiled = str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "ON CONFLICT ON CONSTRAINT graph_version_pkey DO UPDATE" in compiled
    assert "graph_version.version + 1" in compiled
    assert "RETURNING graph_version.version" in compiled
    session.expire.assert_called_once_with(cached)


def test_get_or_create_uses_postgresql_on_conflict_do_nothing() -> None:
    """PostgreSQL get_or_create() avoids UniqueViolation via ON CONFLICT DO NOTHING."""
    session = _make_pg_mock_session()
    expected = GraphVersionModel(tenant_id="t1", graph_id="g1", version=0, reason="init")
    session.query.return_value.filter.return_value.first.return_value = expected

    repo = GraphVersionRepo(session=session, tenant_id="t1")
    model = repo.get_or_create(session, "g1")

    assert model is expected
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    compiled = str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "ON CONFLICT ON CONSTRAINT graph_version_pkey DO NOTHING" in compiled


def test_set_version_uses_postgresql_on_conflict_upsert() -> None:
    """PostgreSQL set_version() emits atomic INSERT ... ON CONFLICT DO UPDATE."""
    session = _make_pg_mock_session()
    repo = GraphVersionRepo(session=session, tenant_id="t1")
    repo.set_version(session, "g1", 7, "restore")

    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    compiled = str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "ON CONFLICT ON CONSTRAINT graph_version_pkey DO UPDATE" in compiled


def test_sqlite_fallback_round_trip() -> None:
    """Non-PostgreSQL sessions still support get_or_create, bump, and set_version."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[GraphVersionModel.__table__])
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        repo = GraphVersionRepo(session=session, tenant_id="t1")
        created = repo.get_or_create(session, "g1")
        assert created.version == 0
        assert repo.bump(session, "g1", "ingest") == 1
        assert repo.bump(session, "g1", "ingest") == 2
        repo.set_version(session, "g1", 10, "reset")
        assert repo.get_version(session, "g1") == 10
