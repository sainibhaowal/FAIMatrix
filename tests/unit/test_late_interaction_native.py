from __future__ import annotations

from faim_native.core.query.late_interaction_native import (
    score_late_interaction_native,
)
from faim_native.encoding.representation_v2 import build_representation_v2


def test_late_interaction_prefers_phrase_and_semantic_alignment():
    query_repr = build_representation_v2(
        "large language model revenue growth in Munchen before 2026 acquisition"
    )
    strong_repr = build_representation_v2(
        "A large language model drove revenue growth in München before the 2026 acquisition."
    )
    weak_repr = build_representation_v2(
        "Inventory levels changed last week in another warehouse."
    )

    strong = score_late_interaction_native(query_repr=query_repr, doc_repr=strong_repr)
    weak = score_late_interaction_native(query_repr=query_repr, doc_repr=weak_repr)

    assert strong.total > weak.total
    assert strong.components["phrase_maxsim"] > 0.0
    assert strong.components["concept_overlap"] >= 0.0
    assert strong.components["translit_bridge"] > 0.0
    assert strong.components["relation_alignment"] > 0.0
    assert strong.components["temporal_alignment"] > 0.0


def test_late_interaction_explain_surfaces_matching_units():
    query_repr = build_representation_v2("artificial intelligence margin 15% after 2025")
    doc_repr = build_representation_v2(
        "AI margin improved by 15% after 2025 according to the report."
    )

    scored = score_late_interaction_native(query_repr=query_repr, doc_repr=doc_repr)

    matched = scored.explain["matched_units"]
    assert matched["token"] or matched["phrase"]
    assert "alias" in matched
    assert scored.components["alias_bridge"] > 0.0
    assert scored.components["value_alignment"] > 0.0


def test_late_interaction_is_deterministic_and_safe_for_missing_doc_repr():
    query_repr = build_representation_v2("cross lingual revenue translation for the quarter")
    doc_repr = build_representation_v2("translation revenue for the quarter across languages")

    first = score_late_interaction_native(query_repr=query_repr, doc_repr=doc_repr)
    second = score_late_interaction_native(query_repr=query_repr, doc_repr=doc_repr)
    missing = score_late_interaction_native(query_repr=query_repr, doc_repr=None)

    assert first == second
    assert first.components["token_maxsim"] > 0.0
    assert first.components["phrase_maxsim"] > 0.0
    assert missing.total == 0.0
    assert missing.explain["matched_units"] == {}
