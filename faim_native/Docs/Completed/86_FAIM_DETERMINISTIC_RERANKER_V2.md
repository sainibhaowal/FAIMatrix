# 86 - FAIM Deterministic Reranker V2

## 1. Status
Completed for the current FAIM runtime contract.

This document now reflects the shipped deterministic reranker used by FAIM
query flow today. It is a real runtime scoring layer, not a future concept.

## 2. What is real

- entity overlap scoring is real
- temporal overlap scoring is real
- proposition overlap scoring is real
- evidence-span scoring is real
- pairwise dominance suppression is real
- duplicate/conflict pruning is real
- reranker-v2 explain payloads are real

## 3. Runtime behavior

FAIM reranker v2 currently:

1. extracts structured proposition and evidence signals
2. scores candidates with entity, time, proposition, and evidence alignment
3. suppresses redundant candidates when they conflict or duplicate each other
4. prefers newer facts when temporal conflicts exist
5. attaches transparent explain payloads to the final query result

## 4. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/core/query/reranker_v2.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`

## 5. User-visible effect

Users see the impact of this layer in:

- cleaner final ranking
- better handling of close candidates
- stronger preference for proposition match
- temporal conflict suppression
- explainable score components in the response payload

## 6. Runtime truth

This is a real FAIM reranking subsystem. It is deterministic, auditable, and
part of the shipped retrieval stack.

## 7. Validation

Relevant runtime coverage is already present in:

- `tests/unit/test_reranker_v2.py`
- `tests/acceptance/test_AT_RR1_proposition_match.py`
- `tests/unit/test_transitive_contradiction.py`
- `tests/acceptance/test_AT_CORTEX_turn.py`

---

*Status: Completed and reconciled to runtime truth*
