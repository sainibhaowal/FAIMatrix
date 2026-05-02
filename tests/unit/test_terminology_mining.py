from __future__ import annotations

from uuid import uuid4

from faim_native.core.operators.terminology_mining import (
    build_domain_document,
    mine_terminology,
)


def test_terminology_mining_extracts_domain_terms_and_aliases():
    docs = [
        build_domain_document(uuid4(), "ARR revenue forecast for Q1"),
        build_domain_document(uuid4(), "ARR revenue planning update"),
    ]
    rows = mine_terminology(docs, domain_pack="finance")
    kinds = {(row["surface_form"], row["kind"]) for row in rows}
    assert ("arr", "domain_term") in kinds
    assert any(row["kind"] == "domain_term" for row in rows)
