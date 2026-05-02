"""Unit tests for deterministic alias and acronym mining."""

from __future__ import annotations

from faim_native.lexical.alias_miner import mine_alias_candidates


def test_mine_alias_candidates_extracts_acronym_and_alias():
    rows = mine_alias_candidates(
        [
            "Retrieval Control Plane (RCP) schedules jobs.",
            "RCP also known as orchestration core manages queues.",
        ]
    )

    by_key = {(row.surface_form, row.canonical_form, row.kind): row for row in rows}
    assert ("rcp", "retrieval control plane", "acronym") in by_key
    assert ("rcp", "orchestration core manages queues", "alias") not in by_key
    assert any(row.kind == "alias" for row in rows)
