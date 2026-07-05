# Phase 8: Long-Tail Knowledge and Domain Adaptation

Phase 8 adds a deterministic offline knowledge layer to FAIM-Native.

## Scope

- offline KB import path
- graph-scoped domain lexicon
- entity / relation / fact / value / time nodes
- additive domain knowledge edges
- domain profile packs
- terminology mining from stored corpus text
- query-time entity linking and fact-support scoring

## Runtime Shape

1. import curated KB rows through the storage domain-knowledge route
2. rebuild graph-scoped domain lexicon from stored files if needed
3. query resolves alias and domain-term matches
4. query expands through entity/fact/value/time graph structure
5. reranker adds bounded domain signals without replacing FAIM base scoring

## Safety Constraints

- additive only
- tenant-scoped and graph-scoped only
- no mutation of `v_native`
- no destructive merge or pruning
- bounded domain score contribution

## Backend Areas

- `core/operators/domain_knowledge.py`
- `core/operators/entity_linking.py`
- `core/operators/terminology_mining.py`
- `orchestration/domain_knowledge_import.py`
- `orchestration/domain_profile_rebuild.py`
- `store/pg/repos/domain_knowledge_repo.py`
- `api/routers/storage.py`
- `orchestration/query_flow.py`
- `core/query/query_engine.py`

## Validation

Phase 8 is verified by:

- unit tests for terminology mining
- unit tests for entity linking
- acceptance tests for KB import
- acceptance tests for domain-linked query scoring
- storage contract regression coverage
