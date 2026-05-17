"""Unit tests for Representation V2 determinism and channel extraction."""

from __future__ import annotations

import sys
from pathlib import Path

_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import BlockAnchor, EvidenceBlock  # noqa: E402
from encoding.representation_v2 import (  # noqa: E402
    build_query_representation_v2,
    build_representation_v2,
    build_representation_v2_for_block,
)


class TestRepresentationV2Determinism:
    def test_same_text_same_repr_hash(self):
        text = "Release 2026 revenue reached 15 percent in Berlin."
        repr1 = build_representation_v2(text)
        repr2 = build_representation_v2(text)

        assert repr1.repr_hash == repr2.repr_hash
        assert repr1.word_counts == repr2.word_counts
        assert repr1.phrase_counts == repr2.phrase_counts
        assert repr1.skip_counts == repr2.skip_counts

    def test_block_layout_tokens_are_deterministic(self):
        block = EvidenceBlock.create(
            raw_id="raw-1",
            anchor=BlockAnchor(
                doc_type="text", char_start=0, char_end=120, section="Intro"
            ),
            content="Invoice INV-2026 was issued on 2026-04-12.",
            block_type="text",
        )

        repr_v2 = build_representation_v2_for_block(block)

        assert "block_type:text" in repr_v2.layout_tokens
        assert "doc_type:text" in repr_v2.layout_tokens
        assert "section:intro" in repr_v2.layout_tokens
        assert repr_v2.channel_lengths["layout"] >= 3

    def test_query_representation_is_deterministic(self):
        query = "NYC revenue in 2026"
        repr1 = build_query_representation_v2(query)
        repr2 = build_query_representation_v2(query)

        assert repr1.repr_hash == repr2.repr_hash
        assert repr1.channel_lengths == repr2.channel_lengths

    def test_entity_and_time_tokens_extracted(self):
        repr_v2 = build_representation_v2(
            "Contact alice@example.com before 2026-04-12 and reference INV-2026."
        )

        assert "alice@example.com" in repr_v2.entity_tokens
        assert "inv-2026" in repr_v2.entity_tokens
        assert "date:2026-04-12" in repr_v2.time_tokens
        assert "year:2026" in repr_v2.time_tokens
