from __future__ import annotations

from faim_native.core.query.answer_synthesis import synthesize_answer


def test_answer_synthesis_surfaces_contradiction_notes():
    answer = synthesize_answer(
        query_text="Where does Atlas live?",
        ranked_results=[
            {
                "node_id": "n1",
                "answer_text": "Atlas lives in Berlin.",
                "evidence": {"raw_id": "raw-1", "block_id": "b1", "anchor": {}},
                "phase4_explain": {
                    "doc_propositions": [
                        {
                            "entity": "atlas",
                            "relation": "rel:about",
                            "value": "berlin",
                            "time": "",
                        }
                    ]
                },
                "temporal_status": "CURRENT",
                "score": 0.9,
            },
            {
                "node_id": "n2",
                "answer_text": "Atlas lives in Munich.",
                "evidence": {"raw_id": "raw-2", "block_id": "b2", "anchor": {}},
                "phase4_explain": {
                    "doc_propositions": [
                        {
                            "entity": "atlas",
                            "relation": "rel:about",
                            "value": "munich",
                            "time": "",
                        }
                    ]
                },
                "temporal_status": "CURRENT",
                "score": 0.8,
            },
        ],
        query_hash="qh",
        graph_id="g",
    )
    assert answer["contradiction_notes"]
