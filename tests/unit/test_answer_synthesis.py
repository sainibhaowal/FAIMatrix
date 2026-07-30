from __future__ import annotations

from faim_native.core.query.answer_synthesis import synthesize_answer


def test_answer_synthesis_returns_citation_first_answer():
    answer = synthesize_answer(
        query_text="Where does Atlas live in 2026?",
        ranked_results=[
            {
                "node_id": "n1",
                "answer_text": "Atlas lives in Berlin in 2026.",
                "evidence": {
                    "raw_id": "raw-1",
                    "block_id": "b1",
                    "anchor": {"page": 1},
                },
                "phase4_explain": {
                    "doc_propositions": [
                        {
                            "entity": "atlas",
                            "relation": "rel:about",
                            "value": "berlin",
                            "time": "year:2026",
                        }
                    ]
                },
                "temporal_status": "CURRENT",
                "score": 0.95,
            }
        ],
        query_hash="qh",
        graph_id="g1",
    )
    assert answer["direct_answer"] == "Atlas lives in Berlin in 2026."
    assert answer["citations"][0]["raw_id"] == "raw-1"
    assert answer["confidence"] > 0.0
