# Phase 5: Scale and Deterministic ANN

Phase 5 adds deterministic acceleration in front of the existing FAIM graph and rerank pipeline.

## Scope

- sparse inverted index over Representation V2
- WAND-style sparse shortlist pruning
- graph-versioned cached sparse/dense artifacts
- deterministic VP-tree dense shortlist for `v_native`
- stable sparse+dense candidate union
- additive query metrics for stage visibility

## Runtime Shape

1. build query Representation V2
2. fetch or build graph-versioned sparse/dense artifacts
3. sparse postings shortlist via inverted index
4. dense shortlist via deterministic VP-tree
5. stable union of sparse and dense candidates
6. existing graph expansion, diffusion, and reranker continue unchanged

## Determinism Constraints

- no learned models
- no random pivots or random graph levels
- stable posting order by node id
- stable shortlist order by score then node id
- deterministic VP-tree pivot selection by node id

## Safety Constraints

- acceleration is not a second source of truth
- cached artifacts are keyed by graph version and rebuilt when the graph changes
- fallback path remains available
- no mutation of stored vectors or edges
- feature-gated rollout via `FAIM_PHASE5_ENABLED`

## Backend Areas

- `index/inverted_index.py`
- `index/wand.py`
- `index/deterministic_ann.py`
- `store/pg/repos/index_repo.py`
- `orchestration/perf/index_rebuild.py`
- `orchestration/query_flow.py`

## Validation

Phase 5 is verified by:

- unit tests for sparse inverted index determinism
- unit tests for WAND-style shortlist ordering
- unit tests for deterministic VP-tree agreement with exact top-k
- acceptance tests for sparse shortlist behavior
- acceptance tests for ANN exact agreement against exact top-k
- acceptance tests for Phase 5 query pipeline integration
- query regression coverage and full repository suite
