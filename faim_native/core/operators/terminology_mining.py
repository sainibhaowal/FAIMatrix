"""Deterministic terminology mining for Phase 8."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple
from uuid import UUID

from lexical.alias_miner import mine_alias_candidates
from lexical.canonicalizer import canonicalize_text

MIN_TERM_SUPPORT = 2
MAX_TERMS = 64
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_:-]{2,}")


@dataclass(frozen=True)
class DomainDocument:
    node_id: UUID
    text: str
    canonical_text: str
    lemma_tokens: Tuple[str, ...]


def build_domain_document(node_id: UUID, text: str) -> DomainDocument:
    item = canonicalize_text(text)
    return DomainDocument(
        node_id=node_id,
        text=text,
        canonical_text=item.canonical_text,
        lemma_tokens=tuple(item.lemma_tokens),
    )


def extract_phrase_terms(text: str) -> Iterable[str]:
    tokens = [t for t in TOKEN_RE.findall(text.lower()) if len(t) > 2]
    for idx, token in enumerate(tokens):
        yield token
        if idx + 1 < len(tokens):
            yield f"{token} {tokens[idx + 1]}"


def mine_terminology(
    docs: Sequence[DomainDocument],
    *,
    domain_pack: str | None = None,
) -> List[Dict[str, object]]:
    min_term_support = 1 if len(docs) <= 2 else MIN_TERM_SUPPORT
    support = Counter()
    contexts: Dict[str, Counter[str]] = defaultdict(Counter)
    alias_rows: List[Dict[str, object]] = []

    for doc in docs:
        terms = sorted(set(extract_phrase_terms(doc.canonical_text)))
        for term in terms:
            support[term] += 1
            token_set = set(term.split())
            for ctx in set(doc.lemma_tokens):
                if ctx not in token_set:
                    contexts[term][ctx] += 1

    for alias in mine_alias_candidates(doc.canonical_text for doc in docs):
        alias_rows.append(
            {
                "surface_form": alias.surface_form,
                "canonical_form": alias.canonical_form,
                "kind": alias.kind,
                "domain_pack": domain_pack,
                "support_count": alias.support_count,
                "score": 1.0,
                "meta": {"source": "terminology_mining"},
            }
        )

    rows: List[Dict[str, object]] = []
    for term, count in sorted(support.items(), key=lambda item: (-item[1], item[0]))[
        :MAX_TERMS
    ]:
        if count < min_term_support:
            continue
        rows.append(
            {
                "surface_form": term,
                "canonical_form": term,
                "kind": "domain_term",
                "domain_pack": domain_pack,
                "support_count": count,
                "score": min(1.0, count / max(len(docs), 1)),
                "meta": {
                    "context_terms": dict(
                        sorted(
                            contexts[term].items(), key=lambda item: (-item[1], item[0])
                        )[:8]
                    )
                },
            }
        )
    return sorted(
        rows + alias_rows,
        key=lambda row: (
            str(row["surface_form"]),
            str(row["kind"]),
            str(row["canonical_form"]),
        ),
    )


__all__ = [
    "DomainDocument",
    "build_domain_document",
    "extract_phrase_terms",
    "mine_terminology",
]
