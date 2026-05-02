from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from faim_native.encoding.representation_v2 import build_representation_v2
from faim_native.index.inverted_index import InvertedIndex


def _row(text: str):
    repr_v2 = build_representation_v2(text)
    return SimpleNamespace(
        node_id=uuid4(),
        repr_hash=repr_v2.repr_hash,
        normalized_text=repr_v2.normalized_text,
        word_counts=repr_v2.word_counts,
        phrase_counts=repr_v2.phrase_counts,
        skip_counts=repr_v2.skip_counts,
        entity_tokens=list(repr_v2.entity_tokens),
        time_tokens=list(repr_v2.time_tokens),
        layout_tokens=list(repr_v2.layout_tokens),
        channel_lengths=repr_v2.channel_lengths,
    )


def test_inverted_index_build_and_match_deterministic():
    row_a = _row("Berlin revenue planning 2026")
    row_b = _row("Warehouse inventory adjusted yesterday")
    index = InvertedIndex.build([row_a, row_b])
    query_repr = build_representation_v2("Berlin revenue 2026")
    matched_1 = index.matching_node_ids(query_repr)
    matched_2 = index.matching_node_ids(query_repr)
    assert matched_1 == matched_2
    assert row_a.node_id in matched_1
    assert row_b.node_id not in matched_1

