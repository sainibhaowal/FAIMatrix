"""Unit tests for deterministic Representation V2 lexical scoring."""

from __future__ import annotations

import sys
from pathlib import Path

_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.query.lexical_scorer import compute_lexical_score  # noqa: E402
from encoding.representation_v2 import build_representation_v2  # noqa: E402


def _stats_for(*reprs):
    stats = {
        channel: {"doc_count": len(reprs), "avg_len": 0.0, "df_map": {}}
        for channel in ("word", "phrase", "skip", "entity", "time", "layout")
    }
    for channel in ("word", "phrase", "skip"):
        total_len = 0
        df_map = {}
        for repr_v2 in reprs:
            total_len += repr_v2.channel_lengths[channel]
            counts = getattr(repr_v2, f"{channel}_counts")
            for term in counts.keys():
                df_map[term] = df_map.get(term, 0) + 1
        stats[channel]["avg_len"] = total_len / max(len(reprs), 1)
        stats[channel]["df_map"] = df_map
    return stats


class TestLexicalScorer:
    def test_matching_doc_scores_higher(self):
        query = build_representation_v2("release 2026 revenue 15 percent")
        doc_match = build_representation_v2("release 2026 revenue reached 15 percent")
        doc_other = build_representation_v2("warehouse inventory adjusted yesterday")
        stats = _stats_for(doc_match, doc_other)

        score_match, components_match = compute_lexical_score(query, doc_match, stats)
        score_other, components_other = compute_lexical_score(query, doc_other, stats)

        assert 0.0 <= score_match <= 1.0
        assert 0.0 <= score_other <= 1.0
        assert score_match > score_other
        assert components_match["word"] >= components_other["word"]

    def test_lexical_score_is_deterministic(self):
        query = build_representation_v2("invoice INV-2026 on 2026-04-12")
        doc = build_representation_v2("invoice INV-2026 was issued on 2026-04-12")
        stats = _stats_for(doc)

        first = compute_lexical_score(query, doc, stats)
        second = compute_lexical_score(query, doc, stats)

        assert first == second
