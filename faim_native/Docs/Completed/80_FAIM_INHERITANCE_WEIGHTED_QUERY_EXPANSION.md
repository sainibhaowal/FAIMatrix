# 80 - FAIM Inheritance-Weighted Query Expansion (IWQE)

## 1. Status
Completed for the current FAIM runtime contract.

FAIM now applies inheritance-weighted query expansion during retrieval. The
query vector is expanded deterministically from parent inheritance vectors and
semantic neighbors before final scoring.

## 2. What is real

The live implementation:

- starts from the 256-dim query vector
- loads seed nodes from initial recall
- fetches inheritance parents for those seeds
- fetches semantic neighbors for those seeds
- blends parent vectors with a weighted inheritance factor
- blends semantic neighbors with a reduced semantic factor
- re-normalizes the final query vector back to unit length

## 3. Why it matters

This improves retrieval because queries can inherit useful context from the
graph instead of relying only on the raw surface text.

It helps FAIM with:

- specific concept lookup
- graph-local parent context
- synonym / hypernym / hyponym / related neighbor recall
- better deterministic candidate ranking

## 4. Runtime truth

The doc is not describing a future-only idea. The expansion is already wired in
the query path:

- first recall seeds
- then call `inheritance_weighted_expansion(...)`
- then continue with graph metrics, retrieval, and reranking

The implementation is additive and keeps the existing vector spine intact.

## 5. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`
- `/home/sephi-asi/FAIM/faim_native/core/operators/semantic_typing.py`
- `/home/sephi-asi/FAIM/faim_native/core/operators/inheritance.py`

Validation:

- `tests/unit/test_weighted_expansion_engine.py`
- `tests/acceptance/test_AT_Q7_query_flow.py`

## 6. What is not a gap

This is not a separate ML model.
It is not a replacement for the canonical vector spine.
It is not a user-visible separate control surface.

It is a deterministic retrieval-time expansion layer.

---

*Status: Completed and reconciled to runtime truth*
