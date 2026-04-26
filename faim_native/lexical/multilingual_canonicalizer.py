"""Deterministic English/German multilingual canonicalization."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

from lexical.de_light_stemmer import stem_de_tokens
from lexical.transliteration import transliterate_de
from lexical.unicode_normalizer import normalize_unicode_text

try:
    from faim.Faim_Native.encoding.porter_stemmer import stem as stem_en
except (ImportError, RuntimeError):
    from encoding.porter_stemmer import stem as stem_en


_WORD_RE = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*")
_RESOURCE_PATH = Path(__file__).parent / "data" / "en_de_lexicon.tsv"
_EN_HINTS = {"the", "and", "is", "revenue", "quarter", "city", "inventory"}
_DE_HINTS = {"und", "ist", "stadt", "umsatz", "quartal", "lager", "bestands"}


@dataclass(frozen=True)
class MultilingualText:
    language: str
    normalized_text: str
    transliterated_text: str
    tokens: Tuple[str, ...]
    stemmed_tokens: Tuple[str, ...]
    expansions: Tuple[str, ...]
    canonical_text: str


def _load_lexicon_rows() -> List[Tuple[str, str, str]]:
    rows: List[Tuple[str, str, str]] = []
    with open(_RESOURCE_PATH, "r", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for row in reader:
            if len(row) != 3 or row[0].startswith("#"):
                continue
            rows.append((row[0].strip(), row[1].strip(), row[2].strip()))
    return rows


def load_en_de_lexicon() -> Dict[str, Dict[str, Tuple[str, str]]]:
    lexicon: Dict[str, Dict[str, Tuple[str, str]]] = {"en": {}, "de": {}}
    for concept_key, en_value, de_value in _load_lexicon_rows():
        lexicon["en"][normalize_unicode_text(en_value)] = (
            concept_key,
            normalize_unicode_text(de_value),
        )
        lexicon["de"][transliterate_de(de_value)] = (
            concept_key,
            normalize_unicode_text(en_value),
        )
    return lexicon


def detect_language(text: str) -> str:
    normalized = normalize_unicode_text(text)
    transliterated = transliterate_de(normalized)
    tokens = set(_WORD_RE.findall(transliterated))
    de_score = len(tokens & _DE_HINTS) + sum(ch in normalized for ch in "äöüß")
    en_score = len(tokens & _EN_HINTS)
    return "de" if de_score > en_score else "en"


def tokenize_text(text: str) -> List[str]:
    return _WORD_RE.findall(text)


def canonicalize_multilingual_text(
    text: str,
    *,
    graph_map: Mapping[str, Sequence[str]] | None = None,
) -> MultilingualText:
    language = detect_language(text)
    normalized = normalize_unicode_text(text)
    transliterated = transliterate_de(normalized)
    tokens = tokenize_text(transliterated)
    if language == "de":
        stemmed = stem_de_tokens(tokens)
    else:
        stemmed = [stem_en(token) for token in tokens]

    lexicon = load_en_de_lexicon()[language]
    expansions: List[str] = []
    canonical_tokens: List[str] = list(stemmed)
    graph_map = graph_map or {}
    for token in stemmed:
        if token in lexicon:
            concept_key, translated = lexicon[token]
            for value in (concept_key, translated):
                if value not in expansions:
                    expansions.append(value)
        for extra in graph_map.get(token, ()):
            if extra not in expansions:
                expansions.append(str(extra))
    for value in expansions:
        if value not in canonical_tokens:
            canonical_tokens.append(value)
    return MultilingualText(
        language=language,
        normalized_text=normalized,
        transliterated_text=transliterated,
        tokens=tuple(tokens),
        stemmed_tokens=tuple(stemmed),
        expansions=tuple(expansions),
        canonical_text=" ".join(canonical_tokens),
    )


__all__ = [
    "MultilingualText",
    "canonicalize_multilingual_text",
    "detect_language",
    "load_en_de_lexicon",
]
