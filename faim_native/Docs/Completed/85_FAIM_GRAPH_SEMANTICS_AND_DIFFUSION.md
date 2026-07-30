# 85 - FAIM Graph Semantics and Diffusion

## 1. Status
Completed for the current FAIM runtime contract.

This document now reflects the shipped graph-semantics layer in FAIM. The
implementation is deterministic, bounded, and part of the live query path.

## 2. What is real

- bounded multi-hop traversal is real
- deterministic diffusion is real
- neighborhood coherence scoring is real
- contradiction-aware suppression is real
- temporal CURRENT/HISTORICAL pruning is real
- graph score fields are emitted into query explain payloads

## 3. Runtime behavior

FAIM graph semantics currently:

1. expands from query seeds into bounded graph neighborhoods
2. propagates support across stable weighted edges
3. computes path support
4. computes fixed-iteration diffusion
5. computes neighborhood coherence
6. suppresses contradicted or older facts
7. blends those signals into a deterministic graph score

## 4. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/core/query/diffusion.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/graph_semantics.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`

## 5. User-visible effect

Users see the impact of this layer in:

- stronger multi-hop recall
- better path-aware evidence
- contradiction suppression for outdated nodes
- graph score components in explain payloads
- FIG View proof surfaces that mirror the query runtime

## 6. Runtime truth

This is a real FAIM retrieval subsystem, not a mock or placeholder. It is
bounded, deterministic, and additive to the rest of the query stack.

## 7. Validation

Relevant runtime coverage is already present in:

- `tests/unit/test_diffusion.py`
- `tests/acceptance/test_AT_GS1_multihop_recall.py`
- `tests/unit/test_transitive_contradiction.py`
- `tests/acceptance/test_AT_CORTEX_turn.py`

---

*Status: Completed and reconciled to runtime truth*
