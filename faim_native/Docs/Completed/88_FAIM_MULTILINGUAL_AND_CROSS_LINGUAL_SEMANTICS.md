# 88 - FAIM Multilingual and Cross-Lingual Semantics

## 1. Status
Completed for the current FAIM runtime contract.

This document now reflects the shipped multilingual semantics layer in FAIM.
The implementation is deterministic, graph-scoped, and wired into query-time
retrieval and multilingual rebuilds.

## 2. What is real

- deterministic language detection is real
- transliteration-safe multilingual normalization is real
- English, German, Spanish, French, Italian, Portuguese, and Dutch resources
  are supported in the shipped multilingual lexicon surface
- cross-lingual concept bridging is real
- graph-scoped multilingual rebuilds are real
- multilingual bridge and concept rows are materialized in the graph

## 3. Runtime behavior

FAIM multilingual semantics currently:

1. detects the language of input text deterministically
2. normalizes and transliterates language-specific surface forms
3. expands known multilingual surfaces into shared concept keys
4. materializes graph-local multilingual lexicon and concept rows
5. reuses those rows during query-time retrieval and explanation
6. keeps the expansion bounded, deterministic, and source-tagged

## 4. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/lexical/multilingual_canonicalizer.py`
- `/home/sephi-asi/FAIM/faim_native/core/operators/multilingual_semantics.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/multilingual_semantics_rebuild.py`
- `/home/sephi-asi/FAIM/faim_native/store/pg/repos/multilingual_repo.py`
- `/home/sephi-asi/FAIM/faim_native/lexical/multilingual_lexicon_builder.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`

## 5. User-visible effect

Users see the impact of this layer in:

- cross-language recall on supported enterprise languages
- deterministic concept-key bridges
- multilingual expansion shown in explain payloads
- graph-local multilingual memory that grows from uploaded content

## 6. Runtime truth

This is a real FAIM retrieval subsystem, not a mock. The shipped runtime is
broader than the original narrow framing, so the doc now reflects the current
enterprise multilingual surface.

## 7. Validation

Relevant runtime coverage is already present in:

- `tests/unit/test_multilingual_canonicalizer.py`
- `tests/unit/test_semantic_registry.py`
- `tests/unit/test_weighted_expansion_engine.py`
- `tests/acceptance/test_AT_ML1_en_de_rebuild.py`
- `tests/acceptance/test_AT_ML2_cross_lingual_query.py`
- `tests/acceptance/test_AT_cross_lingual_recall.py`
- `tests/acceptance/test_AT_CAN2_query_canonical_semantics.py`

---

*Status: Completed and reconciled to runtime truth*
