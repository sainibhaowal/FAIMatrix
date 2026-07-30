from __future__ import annotations

from faim_native.core.query.span_selection import select_supporting_spans


def test_select_supporting_spans_prefers_relevant_sentence():
    spans = select_supporting_spans(
        query_text="Where does Atlas live in 2026?",
        ranked_results=[
            {
                "node_id": "n1",
                "answer_text": "Atlas lives in Berlin in 2026. Warehouse inventory changed yesterday.",
                "evidence": {"raw_id": "raw-1", "block_id": "b1", "anchor": {}},
                "temporal_status": "CURRENT",
                "score": 0.9,
            }
        ],
    )
    assert spans
    assert "Atlas lives in Berlin in 2026." == spans[0].text
