"""Unit tests for Phase 2 canonical semantics mining."""

from __future__ import annotations

from uuid import uuid4

from faim_native.core.operators.canonical_semantics import (
    build_canonical_document,
    build_canonical_semantics,
)


def _doc(text: str):
    return build_canonical_document(
        node_id=uuid4(),
        raw_id=str(uuid4()),
        anchor_json={"doc_type": "text", "char_start": 0, "char_end": len(text)},
        text=text,
    )


def test_build_canonical_semantics_mines_distributional_and_paraphrase_edges():
    docs = [
        _doc("Atlas resides in Berlin. Revenue growth improved this quarter."),
        _doc("Atlas lives in Berlin. Sales growth improved this quarter."),
        _doc("Revenue sales margin improved this quarter."),
        _doc("Budget cost planning for next quarter."),
        _doc("Demand forecast planning continues next quarter."),
    ]

    build = build_canonical_semantics(docs)

    lexicon_keys = {
        (row["surface_form"], row["canonical_form"], row["kind"])
        for row in build.lexicon_entries
    }
    edge_kinds = {row["kind"] for row in build.edge_specs}
    term_channels = {row["channel"] for row in build.term_stats}

    assert ("sale", "revenue", "distributional_synonym") in lexicon_keys
    assert ("resides in", "rel:located_in", "phrase_pattern") in lexicon_keys
    assert "term" in term_channels
    assert "phrase" in term_channels
    assert "distributional_synonym" in edge_kinds
    assert "paraphrase" in edge_kinds
