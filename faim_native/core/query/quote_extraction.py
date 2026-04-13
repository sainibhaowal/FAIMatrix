"""Deterministic quote extraction for Phase 9."""

from __future__ import annotations

from typing import Iterable, List

from core.query.span_selection import CandidateSpan


def extract_quotes(spans: Iterable[CandidateSpan], *, limit: int = 3, max_chars: int = 180) -> List[str]:
    quotes: List[str] = []
    for span in spans:
        text = " ".join(str(span.text).split())
        if not text:
            continue
        if len(text) > max_chars:
            text = text[: max_chars - 3].rstrip() + "..."
        if text not in quotes:
            quotes.append(text)
        if len(quotes) >= limit:
            break
    return quotes


__all__ = ["extract_quotes"]
