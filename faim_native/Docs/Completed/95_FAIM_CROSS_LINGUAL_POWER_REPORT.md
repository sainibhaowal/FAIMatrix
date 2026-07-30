# Phase D: Cross-Lingual Power Report

## Status

Implemented and validated.

## What changed

- The multilingual lexicon loader no longer depends on a single EN/DE TSV only.
- FAIM now loads multilingual lexical resources from `faim_native/lexical/data/*.tsv`.
- FAIM now also loads compressed lexicon packs from `faim_native/lexical/data/*.tsv.gz`.
- A shipped multilingual enterprise pack now exists at `faim_native/lexical/data/multilingual_enterprise_lexicon.tsv.gz`.
- Static concept-key coverage now extends beyond English/German into additional deterministic bridge languages:
  - English
  - German
  - Spanish
  - French
  - Italian
  - Portuguese
  - Dutch
- The current shipped enterprise pack contributes tens of thousands of multilingual surface forms and roughly twenty-eight thousand concept rows on top of the smaller curated TSV seeds.
- Query-time multilingual canonicalization now:
  - detects likely language deterministically
  - matches token and phrase surfaces
  - applies transliteration-safe normalization
  - emits concept keys
  - emits anchor translations
  - emits bounded cross-language bridge forms
- Graph-scoped multilingual rebuild rows now persist richer `bridge_forms` metadata so live graph language mappings can broaden retrieval more effectively.

## Safety properties

- Additive only: this does not replace `v_native`.
- Deterministic only: no stochastic translation model or external ML dependency.
- Bounded only: multilingual bridge expansions remain capped and source-tagged.
- Explainable only: sources remain visible as `multilingual_concept`, `multilingual_translation`, `multilingual_bridge`, and `graph_multilingual`.

## Real effect on retrieval

Before Phase D, multilingual power was effectively strongest for EN/DE only.

After Phase D:

- FAIM can widen the query surface across multiple supported languages through concept-key alignment.
- Cross-language recall is stronger for token, phrase, and concept-level matching.
- Graph rebuild metadata now gives the query path more multilingual bridge candidates from graph-local content.

## Files involved

- `faim_native/lexical/data/multilingual_core_lexicon.tsv`
- `faim_native/lexical/data/multilingual_enterprise_lexicon.tsv.gz`
- `faim_native/lexical/multilingual_canonicalizer.py`
- `faim_native/lexical/multilingual_lexicon_builder.py`
- `faim_native/lexical/transliteration.py`
- `faim_native/core/operators/multilingual_semantics.py`
- `faim_native/orchestration/multilingual_semantics_rebuild.py`
- `faim_native/store/pg/repos/multilingual_repo.py`
- `tests/unit/test_multilingual_canonicalizer.py`
- `tests/unit/test_weighted_expansion_engine.py`
- `tests/acceptance/test_AT_ML1_en_de_rebuild.py`
- `tests/acceptance/test_AT_ML2_cross_lingual_query.py`

## Validation target

Phase D is complete when:

- multilingual canonicalization supports more than EN/DE
- compressed multilingual enterprise packs load at runtime
- rebuild writes multilingual lexicon rows with bridge metadata
- query explain shows multilingual source activity
- acceptance tests prove broader cross-language retrieval behavior
