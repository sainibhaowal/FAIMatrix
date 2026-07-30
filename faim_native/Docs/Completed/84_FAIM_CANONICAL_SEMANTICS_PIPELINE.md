# 84 - FAIM Canonical Semantics Pipeline

## 1. Status
Completed for the current FAIM runtime contract.

This document now describes the shipped canonical-semantics pipeline as it
exists in FAIM today. It is a deterministic retrieval and graph-materialization
layer, not a speculative future architecture note.

## 2. What is real

- Unicode and whitespace normalization are real preprocessing steps
- stop-word removal is real and deterministic
- alias and acronym bridging are real
- phrase-pattern canonicalization is real
- canonical expansion feeds query-time retrieval
- graph-scoped canonical semantics rebuilds are real
- mined distributional and paraphrase edges are materialized into the graph

## 3. Runtime behavior

FAIM canonical semantics currently does the following:

1. normalizes input text into a stable canonical form
2. removes noise from stop words and surface variation
3. maps known aliases and phrase patterns into canonical terms
4. expands the query-time surface deterministically
5. mines graph-local distributional candidates from stored corpus text
6. materializes graph-scoped canonical lexicon rows and semantic edges
7. uses the rebuilt artifacts during retrieval and explanation flows

## 4. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/lexical/canonicalizer.py`
- `/home/sephi-asi/FAIM/faim_native/core/operators/canonical_semantics.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/canonical_semantics_rebuild.py`
- `/home/sephi-asi/FAIM/faim_native/store/pg/repos/canonical_semantics_repo.py`
- `/home/sephi-asi/FAIM/faim_native/api/routers/storage.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`

## 5. User-visible effect

Users do not see a separate "canonical semantics" screen. They see the result
of this layer in the behavior of FAIM:

- better alias matching
- stronger phrase matching
- cleaner lexical grounding
- graph-local canonical proof in query traces
- deterministic behavior across repeated runs

## 6. Runtime truth

This is a real FAIM retrieval subsystem.

It is additive, deterministic, and graph-scoped. It improves query grounding,
but it does not replace the rest of the retrieval stack by itself.

## 7. Validation

Relevant runtime coverage is already present in:

- `tests/unit/test_canonical_semantics.py`
- `tests/unit/test_canonical_semantics_repo.py`
- `tests/acceptance/test_AT_CAN1_canonical_semantics_rebuild.py`
- `tests/acceptance/test_AT_CAN2_query_canonical_semantics.py`

---

*Status: Completed and reconciled to runtime truth*
