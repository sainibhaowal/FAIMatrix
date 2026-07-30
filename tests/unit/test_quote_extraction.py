from __future__ import annotations

from faim_native.core.query.quote_extraction import extract_quotes
from faim_native.core.query.span_selection import CandidateSpan


def test_extract_quotes_deduplicates_and_truncates():
    spans = [
        CandidateSpan(
            "n1", "r1", "b1", {}, "Alpha beta gamma delta.", 0.8, 0, None, 0.9
        ),
        CandidateSpan(
            "n2", "r2", "b2", {}, "Alpha beta gamma delta.", 0.7, 1, None, 0.8
        ),
    ]
    quotes = extract_quotes(spans, limit=2)
    assert quotes == ["Alpha beta gamma delta."]
