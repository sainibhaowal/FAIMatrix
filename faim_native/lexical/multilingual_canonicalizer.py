"""Deterministic multilingual canonicalization and bridge expansion."""

from __future__ import annotations

import csv
import gzip
import re
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from lexical.de_light_stemmer import stem_de_tokens
from lexical.synonym_expander import WeightedExpansion, merge_weighted_expansions
from lexical.transliteration import transliterate_de, transliterate_text
from lexical.unicode_normalizer import normalize_unicode_text

try:
    from faim.Faim_Native.encoding.porter_stemmer import stem as stem_en
except (ImportError, RuntimeError):
    from encoding.porter_stemmer import stem as stem_en


_WORD_RE = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*")
_RESOURCE_DIR = Path(__file__).parent / "data"
_LANG_ALIASES = {
    "english": "en",
    "german": "de",
    "spanish": "es",
    "french": "fr",
    "italian": "it",
    "portuguese": "pt",
    "dutch": "nl",
    "en": "en",
    "de": "de",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "pt": "pt",
    "nl": "nl",
}
_LANGUAGE_HINTS: Dict[str, Tuple[str, ...]] = {
    "en": ("the", "and", "is", "for", "with", "revenue", "quarter"),
    "de": ("und", "ist", "mit", "umsatz", "quartal", "stadt", "lager"),
    "es": ("el", "la", "de", "con", "para", "ingresos", "trimestre"),
    "fr": ("le", "la", "de", "avec", "pour", "revenus", "trimestre"),
    "it": ("il", "la", "di", "con", "per", "ricavi", "trimestre"),
    "pt": ("o", "a", "de", "com", "para", "receita", "trimestre"),
    "nl": ("de", "het", "met", "voor", "omzet", "kwartaal"),
}
_LIGHT_SUFFIXES: Dict[str, Tuple[str, ...]] = {
    "es": ("aciones", "acion", "mente", "adora", "adores", "ador", "idad", "idades", "mente", "ismo", "ista", "istas", "cion", "sion", "es", "s"),
    "fr": ("ements", "ement", "atrices", "atrice", "ateur", "ation", "ations", "euses", "euse", "eaux", "aux", "es", "s"),
    "it": ("azioni", "azione", "mente", "atori", "atore", "trice", "zioni", "zione", "ita", "ita'", "i", "e"),
    "pt": ("acoes", "acao", "mente", "idades", "idade", "adores", "ador", "coes", "cao", "es", "s"),
    "nl": ("heden", "iteit", "eren", "eren", "ing", "ingen", "baar", "lijk", "en", "s"),
}


@dataclass(frozen=True)
class LexiconMatch:
    concept_key: str
    anchor_term: str
    bridge_terms: Tuple[str, ...]


@dataclass(frozen=True)
class MultilingualText:
    language: str
    normalized_text: str
    transliterated_text: str
    tokens: Tuple[str, ...]
    stemmed_tokens: Tuple[str, ...]
    supported_languages: Tuple[str, ...]
    expansions: Tuple[str, ...]
    canonical_text: str
    weighted_expansions: Tuple[WeightedExpansion, ...] = ()


def _normalize_surface(surface: str, language: str) -> str:
    return transliterate_text(surface, language=language)


def _stem_token(language: str, token: str) -> str:
    token = (token or "").strip().lower()
    if not token:
        return token
    if language == "en":
        return stem_en(token)
    if language == "de":
        return stem_de_tokens([token])[0]
    suffixes = _LIGHT_SUFFIXES.get(language, ())
    if len(token) <= 4:
        return token
    for suffix in suffixes:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def _stem_tokens(language: str, tokens: Iterable[str]) -> List[str]:
    return [_stem_token(language, token) for token in tokens]


def _surface_candidates(language: str, surface: str) -> Tuple[str, ...]:
    normalized = _normalize_surface(surface, language)
    tokens = tokenize_text(normalized)
    stemmed = _stem_tokens(language, tokens)
    values = {normalized}
    if stemmed:
        values.add(" ".join(stemmed))
    return tuple(sorted(value for value in values if value))


def _iter_data_files() -> List[Path]:
    files = [
        path
        for path in sorted(_RESOURCE_DIR.iterdir())
        if path.is_file() and path.name.endswith((".tsv", ".tsv.gz"))
    ]
    return files


def _open_lexicon_file(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def _iter_lexicon_rows() -> List[Tuple[str, Dict[str, str]]]:
    rows: List[Tuple[str, Dict[str, str]]] = []
    for path in _iter_data_files():
        with _open_lexicon_file(path) as handle:
            raw_lines = [line.rstrip("\n") for line in handle]
        header: List[str] | None = None
        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                continue
            plain_candidate = [part.strip() for part in stripped.split("\t")]
            if plain_candidate and plain_candidate[0].lower() == "concept_key":
                header = plain_candidate
                continue
            if stripped.startswith("#"):
                candidate = [part.strip() for part in stripped.lstrip("#").split("\t")]
                if candidate and candidate[0].lower() == "concept_key":
                    header = candidate
                continue
            parts = [part.strip() for part in line.split("\t")]
            if len(parts) < 3:
                continue
            if header and len(header) == len(parts):
                concept_key = parts[0]
                surfaces: Dict[str, str] = {}
                for name, value in zip(header[1:], parts[1:]):
                    lang = _LANG_ALIASES.get(name.strip().lower())
                    if lang and value:
                        surfaces[lang] = value
                if surfaces:
                    rows.append((concept_key, surfaces))
                continue
            if len(parts) == 3:
                concept_key, en_value, de_value = parts
                rows.append((concept_key, {"en": en_value, "de": de_value}))
    return rows


@lru_cache(maxsize=1)
def load_multilingual_resources() -> Tuple[
    Dict[str, Dict[str, LexiconMatch]],
    Dict[str, Dict[str, str]],
    Tuple[str, ...],
]:
    concept_surfaces: Dict[str, Dict[str, str]] = {}
    for concept_key, surfaces in _iter_lexicon_rows():
        mapped = concept_surfaces.setdefault(concept_key, {})
        for language, surface in surfaces.items():
            if surface:
                mapped[language] = _normalize_surface(surface, language)

    by_language: Dict[str, Dict[str, LexiconMatch]] = {}
    all_languages = sorted(
        {language for surfaces in concept_surfaces.values() for language in surfaces}
    )
    for concept_key, surfaces in sorted(concept_surfaces.items()):
        anchor = surfaces.get("en") or next(iter(surfaces.values()))
        for language, surface in surfaces.items():
            bridge_terms = tuple(
                value
                for other_language, value in sorted(surfaces.items())
                if other_language != language and value
            )
            entry = LexiconMatch(
                concept_key=concept_key,
                anchor_term=anchor,
                bridge_terms=bridge_terms,
            )
            language_map = by_language.setdefault(language, {})
            for candidate in _surface_candidates(language, surface):
                language_map[candidate] = entry
    return by_language, concept_surfaces, tuple(all_languages)


def load_multilingual_lexicon() -> Dict[str, Dict[str, Tuple[str, str]]]:
    by_language, _concept_surfaces, supported_languages = load_multilingual_resources()
    lexicon: Dict[str, Dict[str, Tuple[str, str]]] = {language: {} for language in supported_languages}
    for language, mapping in by_language.items():
        for surface, match in mapping.items():
            lexicon.setdefault(language, {})[surface] = (
                match.concept_key,
                match.anchor_term,
            )
    return lexicon


def load_en_de_lexicon() -> Dict[str, Dict[str, Tuple[str, str]]]:
    lexicon = load_multilingual_lexicon()
    return {language: lexicon.get(language, {}) for language in ("en", "de")}


def detect_language(text: str) -> str:
    normalized = normalize_unicode_text(text)
    transliterated = transliterate_text(normalized)
    tokens = set(_WORD_RE.findall(transliterated))
    lexicon, _concept_surfaces, supported_languages = load_multilingual_resources()
    best_language = "en"
    best_score = -1
    for language in supported_languages:
        score = 0
        hints = set(_LANGUAGE_HINTS.get(language, ()))
        score += len(tokens & hints)
        language_map = lexicon.get(language, {})
        for token in tokens:
            if token in language_map:
                score += 2
        if language == "de":
            score += sum(ch in normalized for ch in "äöüß")
        if score > best_score:
            best_language = language
            best_score = score
    return best_language


def tokenize_text(text: str) -> List[str]:
    return _WORD_RE.findall(text)


def _surface_ngrams(tokens: Sequence[str], max_n: int = 3) -> List[str]:
    values: List[str] = list(tokens)
    for n in range(2, max_n + 1):
        for idx in range(0, max(len(tokens) - n + 1, 0)):
            values.append(" ".join(tokens[idx : idx + n]))
    return values


def canonicalize_multilingual_text(
    text: str,
    *,
    graph_map: Mapping[str, Sequence[str]] | None = None,
) -> MultilingualText:
    language = detect_language(text)
    normalized = normalize_unicode_text(text)
    transliterated = transliterate_text(normalized, language=language)
    tokens = tokenize_text(transliterated)
    stemmed = _stem_tokens(language, tokens)

    lexicon, _concept_surfaces, supported_languages = load_multilingual_resources()
    language_map = lexicon.get(language, {})
    weighted_rows: List[WeightedExpansion] = []
    canonical_tokens: List[str] = list(stemmed)
    graph_map = graph_map or {}
    surfaces = []
    for candidate in _surface_ngrams(tokens) + _surface_ngrams(stemmed):
        if candidate and candidate not in surfaces:
            surfaces.append(candidate)
    for surface in surfaces:
        if surface in language_map:
            match = language_map[surface]
            weighted_rows.append(
                WeightedExpansion(
                    term=str(match.concept_key),
                    weight=0.9,
                    sources=("multilingual_concept",),
                    origins=(surface,),
                )
            )
            weighted_rows.append(
                WeightedExpansion(
                    term=str(match.anchor_term),
                    weight=0.84,
                    sources=("multilingual_translation",),
                    origins=(surface,),
                )
            )
            for bridge in match.bridge_terms[:4]:
                weighted_rows.append(
                    WeightedExpansion(
                        term=str(bridge),
                        weight=0.74,
                        sources=("multilingual_bridge",),
                        origins=(surface,),
                    )
                )
        for extra in graph_map.get(surface, ()):
            weighted_rows.append(
                WeightedExpansion(
                    term=str(extra),
                    weight=0.8,
                    sources=("graph_multilingual",),
                    origins=(surface,),
                )
            )
    weighted_expansions = merge_weighted_expansions(weighted_rows)
    expansions = [item.term for item in weighted_expansions]
    for value in expansions:
        if value not in canonical_tokens:
            canonical_tokens.append(value)
    return MultilingualText(
        language=language,
        normalized_text=normalized,
        transliterated_text=transliterated,
        tokens=tuple(tokens),
        stemmed_tokens=tuple(stemmed),
        supported_languages=supported_languages,
        expansions=tuple(expansions),
        weighted_expansions=weighted_expansions,
        canonical_text=" ".join(canonical_tokens),
    )


__all__ = [
    "MultilingualText",
    "canonicalize_multilingual_text",
    "detect_language",
    "load_multilingual_lexicon",
    "load_multilingual_resources",
    "load_en_de_lexicon",
]
