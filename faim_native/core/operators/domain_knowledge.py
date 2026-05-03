"""Deterministic offline KB ingestion and domain profile support for Phase 8."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class KBFact:
    entity: str
    relation: str
    value: str
    time_value: str = ""
    aliases: Tuple[str, ...] = ()
    source_id: str = ""
    source_kind: str = "kb"
    meta: Mapping[str, object] | None = None


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def entity_key(entity: str) -> str:
    return f"entity:{_norm(entity)}"


def relation_key(relation: str) -> str:
    return f"relation:{_norm(relation)}"


def value_key(value: str) -> str:
    return f"value:{_norm(value)}"


def time_key(value: str) -> str:
    return f"time:{_norm(value)}"


def fact_key(entity: str, relation: str, value: str, time_value: str = "") -> str:
    raw = "|".join((_norm(entity), _norm(relation), _norm(value), _norm(time_value)))
    return f"fact:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def vector_text_for_key(key: str) -> str:
    return key.replace(":", " ")


def source_hash(row: Mapping[str, object]) -> str:
    payload = json.dumps(
        dict(sorted(row.items())), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_domain_profile_pack(domain_pack: Optional[str]) -> List[Dict[str, object]]:
    return []


def build_kb_lexicon_rows(
    facts: Sequence[KBFact],
    *,
    domain_pack: Optional[str] = None,
) -> List[Dict[str, object]]:
    domain_pack = None
    rows: Dict[Tuple[str, str, str], Dict[str, object]] = {}
    for fact in facts:
        e_key = entity_key(fact.entity)
        r_key = relation_key(fact.relation)
        rows[(fact.entity.lower(), e_key, "entity_alias")] = {
            "surface_form": _norm(fact.entity),
            "canonical_form": e_key,
            "kind": "entity_alias",
            "domain_pack": domain_pack,
            "support_count": 1,
            "score": 1.0,
            "meta": {"class": "entity"},
        }
        rows[(fact.relation.lower(), r_key, "relation_alias")] = {
            "surface_form": _norm(fact.relation),
            "canonical_form": r_key,
            "kind": "relation_alias",
            "domain_pack": domain_pack,
            "support_count": 1,
            "score": 1.0,
            "meta": {"class": "relation"},
        }
        for alias in sorted(
            set(_norm(value) for value in fact.aliases if _norm(value))
        ):
            rows[(alias, e_key, "entity_alias")] = {
                "surface_form": alias,
                "canonical_form": e_key,
                "kind": "entity_alias",
                "domain_pack": domain_pack,
                "support_count": 1,
                "score": 0.95,
                "meta": {"class": "entity", "alias": True},
            }
    return [rows[key] for key in sorted(rows)]


__all__ = [
    "KBFact",
    "build_kb_lexicon_rows",
    "entity_key",
    "fact_key",
    "load_domain_profile_pack",
    "relation_key",
    "source_hash",
    "time_key",
    "value_key",
    "vector_text_for_key",
]
