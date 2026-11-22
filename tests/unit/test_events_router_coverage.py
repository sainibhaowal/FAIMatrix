"""Focused contract coverage for the events API and SSE lifecycle."""

from __future__ import annotations

import asyncio
import importlib
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest


def _event(seq: int, kind: str = "FACT", payload: dict | None = None):
    return SimpleNamespace(
        seq=seq,
        id=uuid4(),
        kind=kind,
        ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
        payload=payload or {"seq": seq},
        checksum=f"checksum-{seq}",
    )


def _context(repo):
    return SimpleNamespace(event_repo=repo, session=object(), tenant_id="tenant-1")


@pytest.mark.asyncio
async def test_event_pagination_tail_forward_and_empty_paths():
    from api.routers import events

    tail_calls = {}

    class Repo:
        def list_tail(self, session, **kwargs):
            tail_calls.update(kwargs)
            return [_event(1), _event(2), _event(3)]

        def get_by_seq(self, session, **kwargs):
            tail_calls.update(kwargs)
            return [_event(7), _event(8), _event(9)]

    ctx = _context(Repo())
    tail = await events.list_events(
        "graph-1", after_seq=0, limit=2, tail=True, kinds=" FACT, , EVENT ", ctx=ctx
    )
    assert [item["seq"] for item in tail["events"]] == [2, 3]
    assert tail["has_more"] is True
    assert tail["next_seq"] == 3
    assert tail_calls["kinds"] == ["FACT", "EVENT"]

    forward = await events.list_events(
        "graph-1", after_seq=4, limit=2, tail=True, kinds="", ctx=ctx
    )
    assert [item["seq"] for item in forward["events"]] == [7, 8]
    assert forward["next_seq"] == 8

    class EmptyRepo:
        def get_by_seq(self, session, **kwargs):
            return []

    empty = await events.list_events(
        "graph-1", after_seq=19, limit=2, tail=False, ctx=_context(EmptyRepo())
    )
    assert empty["events"] == []
    assert empty["next_seq"] == 19
    assert empty["has_more"] is False


@pytest.mark.asyncio
async def test_latest_event_snapshot_and_empty_graph():
    from api.routers import events

    latest = _event(9, "ANSWER")

    class Repo:
        def count(self, session, **kwargs):
            return 9

        def get_latest(self, session, **kwargs):
            return latest

        def get_all(self, session, **kwargs):
            return [_event(8, "DIAGNOSTICS_SNAPSHOT", {"graph_hash": "hash-8"}), latest]

    result = await events.get_latest_event("graph-1", ctx=_context(Repo()))
    assert result["last_seq"] == 9
    assert result["last_kind"] == "ANSWER"
    assert result["snapshot_hash"] == "hash-8"
    assert result["event_count"] == 9

    class EmptyRepo:
        def count(self, session, **kwargs):
            return 0

        def get_latest(self, session, **kwargs):
            return None

        def get_all(self, session, **kwargs):
            return []

    result = await events.get_latest_event("empty", ctx=_context(EmptyRepo()))
    assert result["last_seq"] == 0
    assert result["last_kind"] is None
    assert result["last_ts"] is None
    assert result["snapshot_hash"] is None


@pytest.mark.asyncio
async def test_fig_interaction_success_and_rollback_failure():
    from api.routers import events

    stored = _event(4, "FIG_INTERACTION")

    class GoodRepo:
        def emit(self, session, graph_id, kind, payload):
            assert graph_id == "graph-1"
            assert kind == "FIG_INTERACTION"
            assert payload["protocol"] == "pulse-v2"
            assert payload["tenant_id"] == "tenant-1"
            return stored

    session = SimpleNamespace(commit=lambda: None, rollback=lambda: None)
    ctx = SimpleNamespace(event_repo=GoodRepo(), session=session, tenant_id="tenant-1")
    result = await events.append_fig_interaction_event(
        "graph-1", events.FigInteractionBody(pulse={"selection": "node-1"}), ctx
    )
    assert result["stored"] is True
    assert result["seq"] == 4
    assert result["event_id"] == str(stored.id)

    calls = {"rollback": 0}

    class BadRepo:
        def emit(self, *args, **kwargs):
            raise RuntimeError("journal unavailable")

    def rollback():
        calls["rollback"] += 1

    bad_ctx = SimpleNamespace(
        event_repo=BadRepo(),
        session=SimpleNamespace(commit=lambda: None, rollback=rollback),
        tenant_id="tenant-1",
    )
    result = await events.append_fig_interaction_event(
        "graph-1", events.FigInteractionBody(), bad_ctx
    )
    assert result == {
        "stored": False,
        "graph_id": "graph-1",
        "tenant_id": "tenant-1",
        "error": "pulse_append_failed",
    }
    assert calls["rollback"] == 1

    class BrokenRollback:
        def emit(self, *args, **kwargs):
            raise RuntimeError("journal unavailable")

    broken = SimpleNamespace(
        event_repo=BrokenRollback(),
        session=SimpleNamespace(
            commit=lambda: None,
            rollback=lambda: (_ for _ in ()).throw(RuntimeError("rollback failed")),
        ),
        tenant_id="tenant-1",
    )
    result = await events.append_fig_interaction_event(
        "graph-1", events.FigInteractionBody(), broken
    )
    assert result["stored"] is False


def test_fresh_session_closes_even_when_body_raises(monkeypatch):
    import runtime.context as runtime_context
    from api.routers import events

    session = object()
    closed = []
    monkeypatch.setattr(runtime_context, "get_session", lambda: session)
    monkeypatch.setattr(
        runtime_context, "close_session", lambda value: closed.append(value)
    )

    with pytest.raises(RuntimeError, match="body failure"):
        with events._get_fresh_session() as value:
            assert value is session
            raise RuntimeError("body failure")
    assert closed == [session]


@pytest.mark.asyncio
async def test_sse_generator_negative_start_events_and_cancel(monkeypatch):
    import store.pg.repos.event_repo as event_repo_module
    from api.routers import events

    class FakeRepo:
        def __init__(self, tenant_id):
            assert tenant_id == "tenant-1"

        def get_max_seq(self, session, graph_id):
            assert graph_id == "graph-1"
            return 5

        def get_by_seq(self, session, **kwargs):
            if kwargs["after_seq"] == 5:
                return [_event(6, "NODE_CREATED")]
            return []

    @contextmanager
    def fresh_session():
        yield object()

    monkeypatch.setattr(event_repo_module, "EventRepo", FakeRepo)
    monkeypatch.setattr(events, "_get_fresh_session", fresh_session)

    async def cancel_sleep(_delay):
        raise asyncio.CancelledError

    monkeypatch.setattr(events.asyncio, "sleep", cancel_sleep)
    output = []
    async for chunk in events._event_generator("tenant-1", "graph-1", -1):
        output.append(chunk)
    assert output[0] == "event: ready\n"
    assert '"last_seq": 5' in output[1]
    assert "event: NODE_CREATED\n" in output
    assert "event: disconnect\n" in output


@pytest.mark.asyncio
async def test_sse_generator_heartbeat_timeout_error_and_generator_exit(monkeypatch):
    import store.pg.repos.event_repo as event_repo_module
    from api.routers import events

    @contextmanager
    def fresh_session():
        yield object()

    monkeypatch.setattr(events, "_get_fresh_session", fresh_session)
    monkeypatch.setattr(events, "POLL_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(events, "HEARTBEAT_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(events, "MAX_EMPTY_POLLS", 1)

    class EmptyRepo:
        def __init__(self, tenant_id):
            pass

        def get_by_seq(self, session, **kwargs):
            return []

    monkeypatch.setattr(event_repo_module, "EventRepo", EmptyRepo)
    output = [chunk async for chunk in events._event_generator("t", "g", 0)]
    assert "event: ping\n" in output
    assert "event: timeout\n" in output

    class ErrorRepo:
        def __init__(self, tenant_id):
            pass

        def get_by_seq(self, session, **kwargs):
            raise RuntimeError("poll failed")

    monkeypatch.setattr(event_repo_module, "EventRepo", ErrorRepo)
    output = [chunk async for chunk in events._event_generator("t", "g", 0)]
    assert "event: error\n" in output
    assert any("poll failed" in chunk for chunk in output)

    # Closing a suspended generator exercises the client-disconnect cleanup.
    monkeypatch.setattr(event_repo_module, "EventRepo", EmptyRepo)
    monkeypatch.setattr(events, "MAX_EMPTY_POLLS", 300)
    generator = events._event_generator("t", "g", 0)
    assert await generator.__anext__() == "event: ready\n"
    await generator.aclose()


@pytest.mark.asyncio
async def test_stream_route_returns_configured_sse_response():
    from api.routers import events

    response = await events.stream_events(
        SimpleNamespace(), "graph-1", after_seq=-1, tenant_id="tenant-1"
    )
    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"
    assert response.headers["x-accel-buffering"] == "no"


def test_events_router_bootstraps_native_import_path(monkeypatch):
    import api.routers.events as events

    native_root = str(events._parent)
    original = list(sys.path)
    monkeypatch.setattr(
        sys, "path", [entry for entry in original if entry != native_root]
    )
    importlib.reload(events)
    assert native_root in sys.path
