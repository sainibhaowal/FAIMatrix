"""Representation V2 - additive lexical-semantic sidecar for FAIM.

Keeps the canonical 256-d ``v_native`` contract unchanged while adding
deterministic sparse channels for richer lexical retrieval.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from faim.Faim_Native.core.contracts.types import BlockAnchor, EvidenceBlock
    from faim.Faim_Native.encoding.text_vectorizer import normalize_text
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import BlockAnchor, EvidenceBlock

    from encoding.text_vectorizer import normalize_text


WORD_BUCKETS = 4096
PHRASE_BUCKETS = 4096
SKIP_BUCKETS = 4096

_WORD_RE = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL_RE = re.compile(r"\bhttps?://[^\s]+")
_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_IDENT_RE = re.compile(
    r"\b(?=[A-Za-z0-9_-]*[A-Za-z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*\b"
)
_DATE_RE = re.compile(r"\b(\d{4})[-/](\d{2})[-/](\d{2})\b")
_TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|2100)\b")
_NUMBER_RE = re.compile(r"\b[$€£]?\d+(?:,\d{3})*(?:\.\d+)?%?\b")


@dataclass(frozen=True)
class RepresentationV2:
    """Deterministic sparse representation sidecar."""

    repr_hash: str
    normalized_text: str
    word_counts: Dict[str, int]
    phrase_counts: Dict[str, int]
    skip_counts: Dict[str, int]
    entity_tokens: Tuple[str, ...]
    time_tokens: Tuple[str, ...]
    layout_tokens: Tuple[str, ...]
    channel_lengths: Dict[str, int]

    def to_dict(self) -> Dict[str, object]:
        """Convert to JSON-safe dict."""
        return {
            "repr_hash": self.repr_hash,
            "normalized_text": self.normalized_text,
            "word_counts": dict(self.word_counts),
            "phrase_counts": dict(self.phrase_counts),
            "skip_counts": dict(self.skip_counts),
            "entity_tokens": list(self.entity_tokens),
            "time_tokens": list(self.time_tokens),
            "layout_tokens": list(self.layout_tokens),
            "channel_lengths": dict(self.channel_lengths),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "RepresentationV2":
        """Restore from dict."""
        return cls(
            repr_hash=str(data.get("repr_hash", "")),
            normalized_text=str(data.get("normalized_text", "")),
            word_counts={str(k): int(v) for k, v in dict(data.get("word_counts", {})).items()},  # type: ignore[call-overload]
            phrase_counts={
                str(k): int(v) for k, v in dict(data.get("phrase_counts", {})).items()  # type: ignore[call-overload]
            },
            skip_counts={str(k): int(v) for k, v in dict(data.get("skip_counts", {})).items()},  # type: ignore[call-overload]
            entity_tokens=tuple(str(x) for x in list(data.get("entity_tokens", []))),  # type: ignore[call-overload]
            time_tokens=tuple(str(x) for x in list(data.get("time_tokens", []))),  # type: ignore[call-overload]
            layout_tokens=tuple(str(x) for x in list(data.get("layout_tokens", []))),  # type: ignore[call-overload]
            channel_lengths={
                str(k): int(v) for k, v in dict(data.get("channel_lengths", {})).items()  # type: ignore[call-overload]
            },
        )


def _hash_bucket(term: str, num_buckets: int) -> str:
    digest = hashlib.sha256(term.encode("utf-8")).digest()
    return str(int.from_bytes(digest[:4], "big", signed=False) % num_buckets)


def _count_bucketed(terms: Iterable[str], num_buckets: int) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for term in terms:
        bucket = _hash_bucket(term, num_buckets)
        counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _tokenize_words(text: str) -> List[str]:
    return _WORD_RE.findall(text)


def _build_phrase_terms(tokens: Sequence[str]) -> List[str]:
    phrases: List[str] = []
    for n in (2, 3):
        for i in range(len(tokens) - n + 1):
            phrases.append("|".join(tokens[i : i + n]))
    return phrases


def _build_skip_terms(tokens: Sequence[str]) -> List[str]:
    skip_terms: List[str] = []
    for i in range(len(tokens) - 2):
        skip_terms.append(f"{tokens[i]}|*|{tokens[i + 2]}")
    return skip_terms


def _extract_entity_tokens(raw_text: str) -> Tuple[str, ...]:
    found = set()
    for pattern in (_EMAIL_RE, _URL_RE, _UUID_RE, _IDENT_RE):
        for match in pattern.findall(raw_text):
            found.add(match.lower())
    return tuple(sorted(found))


def _extract_time_tokens(raw_text: str) -> Tuple[str, ...]:
    found = set()
    for year, month, day in _DATE_RE.findall(raw_text):
        found.add(f"date:{year}-{month}-{day}")
        found.add(f"year:{year}")
        found.add(f"month:{month}")
    for match in _TIME_RE.findall(raw_text):
        found.add(f"time:{match}")
    for match in _YEAR_RE.findall(raw_text):
        found.add(f"year:{match}")
    for match in _NUMBER_RE.findall(raw_text):
        found.add(f"num:{match.replace(',', '').lower()}")
    return tuple(sorted(found))


def _extract_layout_tokens(
    block_type: Optional[str],
    anchor: Optional[BlockAnchor],
) -> Tuple[str, ...]:
    tokens = set()
    if block_type:
        tokens.add(f"block_type:{block_type.lower()}")
    if anchor is None:
        return tuple(sorted(tokens))

    tokens.add(f"doc_type:{anchor.doc_type.lower()}")
    if anchor.page is not None:
        tokens.add(f"page:{anchor.page}")
    if anchor.slide is not None:
        tokens.add(f"slide:{anchor.slide}")
    if anchor.sheet:
        tokens.add(f"sheet:{anchor.sheet.lower()}")
    if anchor.section:
        tokens.add(f"section:{anchor.section.lower()}")
    if anchor.char_start is not None and anchor.char_end is not None:
        span = max(0, anchor.char_end - anchor.char_start)
        if span < 200:
            tokens.add("char_span:short")
        elif span < 1000:
            tokens.add("char_span:medium")
        else:
            tokens.add("char_span:long")
    if anchor.row_start is not None and anchor.row_end is not None:
        tokens.add(f"rows:{anchor.row_start}-{anchor.row_end}")
    return tuple(sorted(tokens))


def _compute_repr_hash(payload: Dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_representation_v2(
    text: str,
    *,
    block_type: Optional[str] = None,
    anchor: Optional[BlockAnchor] = None,
    expand_synonyms: bool = False,
    stem: bool = True,
    display_text: Optional[str] = None,
) -> RepresentationV2:
    """Build deterministic sparse lexical representation.

    display_text: if provided, stored as normalized_text for LLM retrieval.
    Defaults to the stemmed/lowercased form when not provided.
    Token matching channels (word_counts etc.) always use the processed form.
    """
    processed = normalize_text(
        text,
        lowercase=True,
        stem=stem,
        remove_stopwords=False,
        expand_synonyms=expand_synonyms,
    )
    tokens = _tokenize_words(processed)
    word_counts = _count_bucketed(tokens, WORD_BUCKETS)
    phrase_counts = _count_bucketed(_build_phrase_terms(tokens), PHRASE_BUCKETS)
    skip_counts = _count_bucketed(_build_skip_terms(tokens), SKIP_BUCKETS)
    entity_tokens = _extract_entity_tokens(text)
    time_tokens = _extract_time_tokens(text)
    layout_tokens = _extract_layout_tokens(block_type, anchor)

    # Store original readable text for LLM answer synthesis.
    # Matching channels (word_counts etc.) use the processed form above.
    # Strip NUL bytes — PostgreSQL rejects strings containing \x00.
    readable_text = (display_text or text).strip().replace("\x00", "")

    channel_lengths = {
        "word": len(tokens),
        "phrase": max(len(tokens) - 1, 0) + max(len(tokens) - 2, 0),
        "skip": max(len(tokens) - 2, 0),
        "entity": len(entity_tokens),
        "time": len(time_tokens),
        "layout": len(layout_tokens),
    }

    canonical = {
        "normalized_text": readable_text,
        "word_counts": word_counts,
        "phrase_counts": phrase_counts,
        "skip_counts": skip_counts,
        "entity_tokens": list(entity_tokens),
        "time_tokens": list(time_tokens),
        "layout_tokens": list(layout_tokens),
        "channel_lengths": channel_lengths,
    }

    return RepresentationV2(
        repr_hash=_compute_repr_hash(canonical),
        normalized_text=readable_text,
        word_counts=word_counts,
        phrase_counts=phrase_counts,
        skip_counts=skip_counts,
        entity_tokens=entity_tokens,
        time_tokens=time_tokens,
        layout_tokens=layout_tokens,
        channel_lengths=channel_lengths,
    )


def build_representation_v2_for_block(block: EvidenceBlock) -> RepresentationV2:
    """Build Representation V2 for an EvidenceBlock."""
    return build_representation_v2(
        block.content,
        block_type=block.block_type,
        anchor=block.anchor,
        expand_synonyms=False,
        stem=True,
        display_text=block.content,  # store original text for LLM retrieval
    )


def build_query_representation_v2(query_text: str) -> RepresentationV2:
    """Build Representation V2 for query text."""
    return build_representation_v2(
        query_text,
        block_type=None,
        anchor=None,
        expand_synonyms=True,
        stem=True,
    )
