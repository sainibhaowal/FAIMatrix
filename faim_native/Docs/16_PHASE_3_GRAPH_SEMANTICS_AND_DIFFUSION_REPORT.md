# 16A - Phase 3 Graph Semantics and Diffusion Report

Phase 3 adds deterministic graph-aware retrieval depth to FAIM-Native.

## Scope

- weighted multi-hop traversal
- bounded graph diffusion
- concept neighborhood scoring
- contradiction-aware path handling
- additive explain support

## Runtime Shape

1. seed recall remains unchanged
2. graph semantics expands and scores a bounded candidate neighborhood
3. graph scores are fused additively into reranking
4. explain payload can surface Phase 3 graph path evidence

## Determinism Constraints

- fixed hop depth
- fixed neighbor caps
- fixed diffusion step count
- stable sorting by score and node id
- no randomness

## Safety Constraints

- no mutation of `v_native`
- no mutation of raw truth
- no cross-tenant or cross-graph traversal
- `opposition` edges penalize/suppress but are not used for expansion
- graph scoring is bounded and additive

## Backend Areas

- `core/query/diffusion.py`
- `core/query/graph_semantics.py`
- `core/query/query_engine.py`
- `orchestration/query_flow.py`
- `store/pg/repos/edge_repo.py`
- `store/pg/repos/node_repo.py`

## Validation

Phase 3 is verified by:

- unit tests for deterministic diffusion and graph semantics
- acceptance tests for multihop recall and contradiction-aware behavior
- query determinism and explain correctness regression coverage
- FIG graph API regression coverage
