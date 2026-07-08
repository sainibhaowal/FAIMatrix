from __future__ import annotations

from uuid import uuid4

from faim_native.core.operators.terminology_mining import build_domain_document
from faim_native.domain.semantic_memory import learn_semantic_memory_bundles


def test_semantic_memory_learning_builds_graph_local_bundle_rows():
    docs = [
        build_domain_document(
            uuid4(),
            "Application Programming Interface (API) latency improved after deployment.",
        ),
        build_domain_document(
            uuid4(),
            "API latency remained stable and the application programming interface improved.",
        ),
    ]

    result = learn_semantic_memory_bundles(docs, domain_pack="software")

    kinds = {row["kind"] for row in result.lexicon_rows}
    assert "concept_bundle" in kinds
    assert "semantic_paraphrase" in kinds
    assert any(row["source_kind"] == "semantic_bundle" for row in result.source_rows)

    bundle_rows = [row for row in result.lexicon_rows if row["kind"] == "concept_bundle"]
    assert bundle_rows
    assert any("bundle_members" in dict(row["meta"] or {}) for row in bundle_rows)


def test_semantic_memory_learning_is_empty_without_multi_term_signal():
    docs = [build_domain_document(uuid4(), "Revenue improved.")]

    result = learn_semantic_memory_bundles(docs, domain_pack="finance")

    assert result.lexicon_rows == ()
    assert result.source_rows == ()
    assert result.semantic_edges == ()
