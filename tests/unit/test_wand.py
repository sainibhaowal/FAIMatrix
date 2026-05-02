from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from faim_native.encoding.representation_v2 import build_representation_v2
from faim_native.index.inverted_index import InvertedIndex
from faim_native.index.wand import block_max_wand_shortlist


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


def test_block_max_wand_shortlist_prefers_relevant_doc():
    rows = [
        _row("Berlin revenue planning 2026 15 percent"),
        _row("Warehouse inventory adjusted yesterday"),
        _row("Berlin planning notes"),
    ]
    index = InvertedIndex.build(rows)
    query_repr = build_representation_v2("Berlin revenue 2026")
    stats = {
        "word": {"doc_count": 3, "avg_len": 4.0, "df_map": {}},
        "phrase": {"doc_count": 3, "avg_len": 2.0, "df_map": {}},
        "skip": {"doc_count": 3, "avg_len": 1.0, "df_map": {}},
        "entity": {"doc_count": 3, "avg_len": 0.0, "df_map": {}},
        "time": {"doc_count": 3, "avg_len": 0.0, "df_map": {}},
        "layout": {"doc_count": 3, "avg_len": 0.0, "df_map": {}},
    }
    ranked = block_max_wand_shortlist(index, query_repr, stats, k=2)
    assert ranked
    assert ranked[0][0] == rows[0].node_id
    assert ranked[0][1] >= ranked[-1][1]

