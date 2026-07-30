"""Regression: /events should clamp oversized limit values instead of 422."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

from api.routers.events import MAX_PAGE_SIZE, list_events


@dataclass
class _FakeEvent:
    seq: int
    id: str
    kind: str
    ts: datetime
    payload: dict
    checksum: str


class _FakeEventRepo:
    def __init__(self) -> None:
        self.last_limit: int | None = None

    def get_by_seq(self, session, graph_id: str, after_seq: int, limit: int):
        self.last_limit = limit
        return [
            _FakeEvent(
                seq=i,
                id=f"evt-{i}",
                kind="EVOLUTION_COMPLETE",
                ts=datetime.now(timezone.utc),
                payload={"i": i},
                checksum=f"chk-{i}",
            )
            for i in range(1, limit + 1)
        ]


def test_events_limit_is_clamped_instead_of_rejected() -> None:
    repo = _FakeEventRepo()
    ctx = SimpleNamespace(
        event_repo=repo,
        session=object(),
        tenant_id="tenant_test",
    )

    # Use a limit above API cap; function should clamp to MAX_PAGE_SIZE.
    result = asyncio.run(
        list_events(
            graph_id="graph_test",
            after_seq=0,
            limit=120,
            ctx=ctx,
        )
    )

    assert repo.last_limit == MAX_PAGE_SIZE + 1
    assert result["count"] == MAX_PAGE_SIZE
    assert result["has_more"] is True
