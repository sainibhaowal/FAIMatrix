"""Unit tests: worker only claims executable job kinds."""

from __future__ import annotations

import orchestration.jobs.worker as worker_mod


def test_worker_uses_filtered_claim_for_executable_kinds(monkeypatch):
    called: dict[str, object] = {}

    class DummySession:
        def close(self):
            return None

    def fake_claim_next_of_kinds(*, session, executable_kinds, timeout_seconds=300):
        called["session"] = session
        called["kinds"] = list(executable_kinds)
        called["timeout_seconds"] = timeout_seconds
        return None

    monkeypatch.setattr(worker_mod, "get_session", lambda: DummySession())
    monkeypatch.setattr(
        worker_mod.JobStore, "claim_next_of_kinds", fake_claim_next_of_kinds
    )

    worker = worker_mod.Worker(poll_interval=0.01)
    worker._poll_and_execute()

    assert called.get("kinds") == [
        "evolve",
        "ingest_secondary_index",
        "storage_retention",
    ]
    assert called.get("timeout_seconds") == 300
