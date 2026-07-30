"""Deterministic offline KB ingestion and autonomous domain profile support."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


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


DOMAIN_PROFILE_PACKS: Dict[str, Tuple[Tuple[str, str, str], ...]] = {
    "general": (
        ("document", "document", "domain_term"),
        ("project", "project", "domain_term"),
        ("policy", "policy", "domain_term"),
        ("process", "process", "domain_term"),
        ("issue", "issue", "domain_term"),
        ("status", "status", "domain_term"),
        ("deadline", "deadline", "domain_term"),
        ("customer", "customer", "domain_term"),
        ("update", "update", "domain_term"),
        ("team", "team", "domain_term"),
    ),
    "finance": (
        ("ebitda", "ebitda", "domain_term"),
        ("gross margin", "gross margin", "domain_term"),
        ("revenue", "relation:revenue", "relation_alias"),
        ("sales", "relation:revenue", "relation_alias"),
        ("operating income", "relation:operating_income", "relation_alias"),
        ("cash flow", "relation:cash_flow", "relation_alias"),
    ),
    "medical": (
        ("hba1c", "hba1c", "domain_term"),
        ("myocardial infarction", "entity:myocardial infarction", "entity_alias"),
        ("heart attack", "entity:myocardial infarction", "entity_alias"),
        ("diagnosis", "relation:diagnosis", "relation_alias"),
        ("treats", "relation:treats", "relation_alias"),
        ("symptom", "relation:symptom", "relation_alias"),
    ),
    "legal": (
        ("retainer agreement", "retainer agreement", "domain_term"),
        ("indemnification", "indemnification", "domain_term"),
        ("agreement", "relation:agreement", "relation_alias"),
        ("contract", "relation:agreement", "relation_alias"),
        ("governing law", "relation:governing_law", "relation_alias"),
        ("effective date", "relation:effective_date", "relation_alias"),
    ),
    "security": (
        ("cve", "cve", "domain_term"),
        ("privilege escalation", "privilege escalation", "domain_term"),
        ("vulnerability", "relation:vulnerability", "relation_alias"),
        ("exploit", "relation:exploit", "relation_alias"),
        ("authentication", "relation:authentication", "relation_alias"),
        ("authorization", "relation:authorization", "relation_alias"),
    ),
    "software": (
        ("api", "api", "domain_term"),
        ("latency", "latency", "domain_term"),
        ("deployment", "relation:deployment", "relation_alias"),
        ("depends on", "relation:depends_on", "relation_alias"),
        ("dependency", "relation:depends_on", "relation_alias"),
        ("service", "relation:service", "relation_alias"),
    ),
}

DOMAIN_PACK_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "general": ("document", "project", "policy", "process", "issue", "status", "update"),
    "finance": ("revenue", "ebitda", "margin", "cash flow", "forecast", "invoice"),
    "medical": ("patient", "diagnosis", "symptom", "treatment", "hba1c", "dosage"),
    "legal": ("agreement", "contract", "clause", "indemnify", "governing law", "party"),
    "security": ("cve", "vulnerability", "exploit", "threat", "authn", "authz"),
    "software": ("api", "deployment", "service", "latency", "database", "runtime"),
}


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


def available_domain_profile_packs() -> Tuple[str, ...]:
    return tuple(sorted(DOMAIN_PROFILE_PACKS))


def _normalize_pack_names(domain_pack: Optional[str]) -> List[str]:
    raw = str(domain_pack or "").strip().lower()
    if not raw:
        return []
    parts = [part.strip() for part in raw.replace("+", ",").split(",")]
    normalized: List[str] = []
    seen = set()
    for part in parts:
        if not part or part not in DOMAIN_PROFILE_PACKS or part in seen:
            continue
        seen.add(part)
        normalized.append(part)
    return normalized


def load_domain_profile_pack(domain_pack: Optional[str]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for pack_name in _normalize_pack_names(domain_pack):
        for surface_form, canonical_form, kind in DOMAIN_PROFILE_PACKS[pack_name]:
            rows.append(
                {
                    "surface_form": surface_form,
                    "canonical_form": canonical_form,
                    "kind": kind,
                    "domain_pack": pack_name,
                    "support_count": 1,
                    "score": 0.65,
                    "meta": {"source": "builtin_domain_pack", "pack": pack_name},
                }
            )
    return rows


def detect_domain_profile_packs(
    texts: Iterable[str],
    *,
    limit: int = 3,
) -> List[str]:
    scores: Counter[str] = Counter()
    for raw_text in texts:
        normalized = " ".join(str(raw_text or "").lower().split())
        if not normalized:
            continue
        for pack_name, keywords in DOMAIN_PACK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized:
                    scores[pack_name] += 1
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    result = [name for name, _score in ranked[: max(1, int(limit))]]
    if not result and any(str(text or "").strip() for text in texts):
        return ["general"]
    if "general" not in result:
        result.append("general")
    return result[: max(1, int(limit))]


def build_kb_lexicon_rows(
    facts: Sequence[KBFact],
    *,
    domain_pack: Optional[str] = None,
) -> List[Dict[str, object]]:
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


def derive_kb_rows_from_documents(
    texts: Sequence[str],
    *,
    source_kind: str = "autonomous_domain",
) -> List[Dict[str, object]]:
    try:
        from core.query.proposition_extractor import extract_propositions
    except Exception:
        return []

    rows: Dict[Tuple[str, str, str, str], Dict[str, object]] = {}
    for index, text in enumerate(texts):
        if not str(text or "").strip():
            continue
        analysis = extract_propositions(str(text))
        for proposition in analysis.propositions[:4]:
            entity = str(proposition.entity or "").strip()
            relation = str(proposition.relation or "").strip()
            value = str(proposition.value or "").strip()
            time_value = str(proposition.time or "").strip()
            if not entity or not relation:
                continue
            if relation == "rel:about" and not value and not time_value:
                continue
            aliases = [
                token
                for token in analysis.entities
                if token and token != entity and len(token) > 2
            ][:4]
            key = (entity, relation, value, time_value)
            row = rows.setdefault(
                key,
                {
                    "entity": entity,
                    "relation": relation,
                    "value": value or "observed",
                    "time": time_value.removeprefix("date:")
                    .removeprefix("year:")
                    .removeprefix("time:"),
                    "aliases": aliases,
                    "source_id": f"auto:{index}:{len(rows)}",
                    "source_kind": source_kind,
                    "meta": {"source": source_kind},
                },
            )
            if aliases:
                merged = list(dict.fromkeys(list(row.get("aliases", [])) + aliases))
                row["aliases"] = merged[:8]
    return [rows[key] for key in sorted(rows)]


__all__ = [
    "KBFact",
    "build_kb_lexicon_rows",
    "available_domain_profile_packs",
    "derive_kb_rows_from_documents",
    "detect_domain_profile_packs",
    "entity_key",
    "fact_key",
    "load_domain_profile_pack",
    "relation_key",
    "source_hash",
    "time_key",
    "value_key",
    "vector_text_for_key",
]
