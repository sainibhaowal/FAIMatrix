# 77 - FAIM Stop Word Removal and Text Canonicalization Report

## 1. Status
Completed for the current FAIM runtime contract.

FAIM performs deterministic text cleanup before retrieval and reasoning. The
layer is real, additive, and wired into the live query path.

## 2. What is real

- stop-word filtering and canonicalization are real preprocessing steps
- these feed into:
  - canonical semantics
  - semantic signature generation
  - semantic registry lookup
  - native vector and lexical retrieval
  - proposition/evidence extraction

## 3. Correct architecture wording

Canonicalization does **not** feed a fake fixed `1M+ registry`.

It feeds the real retrieval stack:

- semantic registry runtime
- graph-local lexicon layers
- semantic signature channels
- reranker and reasoning extraction layers

## 4. Why it matters

This layer removes noise and improves:

- deterministic matching
- canonical term lookup
- multilingual bridging
- proposition extraction
- semantic-signature quality

## 5. Runtime truth

This is a real production retrieval-preprocessing layer. It is already wired
into the query flow and should be documented as part of the modern FAIM
semantic stack.

## 6. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/lexical/canonicalizer.py`
- `/home/sephi-asi/FAIM/faim_native/lexical/semantic_registry.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`
- `/home/sephi-asi/FAIM/faim_native/encoding/text_vectorizer.py`
- `/home/sephi-asi/FAIM/faim_native/core/operators/canonical_semantics.py`
- `/home/sephi-asi/FAIM/faim_native/core/operators/terminology_mining.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/proposition_extractor.py`

Validation sources:

- `tests/unit/test_weighted_expansion_engine.py`
- `tests/unit/test_multilingual_canonicalizer.py`
- `tests/unit/test_semantic_registry.py`
- `tests/acceptance/test_AT_CAN2_query_canonical_semantics.py`
- `tests/acceptance/test_AT_semantic_registry_runtime.py`

---

*Status: Completed and reconciled to runtime truth*
