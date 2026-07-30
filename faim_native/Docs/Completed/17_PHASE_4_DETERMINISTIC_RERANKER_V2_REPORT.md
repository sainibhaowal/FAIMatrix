# 17 - Phase 4 Deterministic Reranker V2 Report

Status: Completed

Phase 4 adds a stronger deterministic reranking layer to FAIM-Native.

## Scope

- proposition extraction
- evidence span scoring
- entity/time/proposition signal fusion
- pairwise dominance suppression
- additive explain fields

## Runtime Shape

1. current FAIM base score is computed
2. lexical and graph signals are fused
3. proposition/evidence/entity/time signals are added
4. bounded pairwise suppression removes weaker duplicate/conflicting candidates

## Determinism Constraints

- no ML models
- no randomness
- stable signature extraction
- stable shortlist ordering
- stable suppression ordering by score and node id

## Safety Constraints

- no mutation of `v_native`
- no mutation of graph edges or raw truth
- shortlist-bounded suppression only
- additive scoring only

## Backend Areas

- `core/query/proposition_extractor.py`
- `core/query/evidence_scoring.py`
- `core/query/reranker_v2.py`
- `core/query/query_engine.py`
- `orchestration/query_flow.py`
- `store/pg/models_faim.py`
- `store/pg/repos/representation_repo.py`

## Validation

Phase 4 is verified by:

- unit tests for proposition extraction
- unit tests for evidence scoring
- unit tests for reranker conflict suppression
- acceptance tests for proposition-aware query ranking
- query regression coverage
