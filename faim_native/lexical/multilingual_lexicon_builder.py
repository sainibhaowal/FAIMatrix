"""Build a larger deterministic multilingual lexicon pack from Open Multilingual WordNet.

Runtime FAIM does not depend on `wn`. This is a one-time/offline builder that
generates a compressed TSV pack FAIM can ship and load directly.
"""

from __future__ import annotations

import csv
import gzip
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

try:
    from lexical.transliteration import transliterate_text
except ImportError:
    _PARENT = Path(__file__).resolve().parent.parent
    if str(_PARENT) not in sys.path:
        sys.path.insert(0, str(_PARENT))
    from lexical.transliteration import transliterate_text

SUPPORTED_LANGS = ("en", "de", "es", "fr", "it", "pt", "nl")
OMW_SPECS = {
    "en": "omw-en:1.4",
    "es": "omw-es:1.4",
    "fr": "omw-fr:1.4",
    "it": "omw-it:1.4",
    "pt": "omw-pt:1.4",
    "nl": "omw-nl:1.4",
}
HEADER = ["concept_key", *SUPPORTED_LANGS]
DEFAULT_MAX_ROWS = 40_000
_UNSAFE_CHARS = re.compile(r"[^a-z0-9 _:/.-]+")


def _slugify(term: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in term.strip().lower())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:72] or "concept"


def _normalize_form(term: str, language: str) -> str:
    normalized = transliterate_text((term or "").replace("_", " "), language=language)
    normalized = _UNSAFE_CHARS.sub(" ", normalized)
    normalized = " ".join(normalized.split()).strip(" .:/-")
    return normalized


def _choose_form(forms: Sequence[str], language: str) -> str:
    normalized = sorted(
        {
            _normalize_form(form, language)
            for form in forms
            if _normalize_form(form, language) and len(_normalize_form(form, language)) <= 80
        },
        key=lambda value: (len(value), value),
    )
    return normalized[0] if normalized else ""


def _import_wn():
    search_path = os.environ.get("FAIM_WN_PYTHONPATH")
    if search_path:
        for part in search_path.split(os.pathsep):
            if part and part not in sys.path:
                sys.path.insert(0, part)
    import wn  # type: ignore

    return wn


def build_omw_pack(*, max_rows: int = DEFAULT_MAX_ROWS) -> List[Dict[str, str]]:
    wn = _import_wn()
    english = wn.Wordnet(OMW_SPECS["en"])
    lexicons = {
        language: wn.Wordnet(spec)
        for language, spec in OMW_SPECS.items()
        if language != "en"
    }

    rows: List[Dict[str, str]] = []
    seen: set[str] = set()
    for synset in english.synsets():
        eng_forms = [form for word in synset.words() for form in word.forms()]
        english_form = _choose_form(eng_forms, "en")
        if not english_form:
            continue
        row = {"concept_key": f"concept:{_slugify(english_form)}", "en": english_form}
        language_count = 1
        for language, lexicon in lexicons.items():
            translated = lexicon.synsets(ili=synset.ili)
            if not translated:
                row[language] = ""
                continue
            forms = [form for word in translated[0].words() for form in word.forms()]
            chosen = _choose_form(forms, language)
            row[language] = chosen
            if chosen:
                language_count += 1
        row["de"] = ""
        if language_count < 2:
            continue
        signature = "|".join(row.get(language, "") for language in HEADER[1:])
        if signature in seen:
            continue
        seen.add(signature)
        rows.append(row)

    rows.sort(
        key=lambda row: (
            -sum(1 for language in SUPPORTED_LANGS if row.get(language)),
            row.get("en", ""),
            row["concept_key"],
        )
    )
    return rows[:max_rows]


def write_pack(output_path: Path, rows: Iterable[Dict[str, str]]) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with gzip.open(output_path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in HEADER})
    return len(rows)


if __name__ == "__main__":
    out = (
        Path(__file__).parent / "data" / "multilingual_enterprise_lexicon.tsv.gz"
    )
    rows = build_omw_pack()
    total = write_pack(out, rows)
    print(f"Wrote {total} multilingual rows to {out}")
