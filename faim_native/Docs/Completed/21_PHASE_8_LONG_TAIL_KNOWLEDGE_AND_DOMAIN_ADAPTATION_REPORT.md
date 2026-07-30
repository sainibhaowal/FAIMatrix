# 21 - Phase 8 Long-Tail Knowledge and Domain Adaptation Report

Status: Completed

Phase 8 adds a deterministic offline knowledge layer to FAIM-Native.

## Scope

- offline KB import path
- graph-scoped domain lexicon
- entity / relation / fact / value / time nodes
- additive domain knowledge edges
- domain profile packs
- terminology mining from stored corpus text
- query-time entity linking and fact-support scoring
- dedicated domain intelligence API and dashboard surface

## Runtime Shape

1. uploads and memory writes can trigger autonomous domain adaptation
2. FAIM mines terminology and detects built-in broad domain packs
3. graph-scoped lexicon, KB source rows, and domain-linked nodes are persisted
4. query resolves alias and domain-term matches
5. query expands through entity/fact/value/time graph structure
6. reranker adds bounded domain signals without replacing FAIM base scoring
7. `/api/v1/domain/*` and `/dashboard/domain` expose what FAIM learned

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
- `orchestration/domain_autonomy.py`
- `domain/intelligence.py`
- `store/pg/repos/domain_knowledge_repo.py`
- `api/routers/storage.py`
- `api/routers/domain.py`
- `orchestration/query_flow.py`
- `core/query/query_engine.py`
- `frontend/src/app/(app)/dashboard/domain/page.tsx`
- `frontend/src/components/domain/DomainKnowledgeGraph.tsx`

## Validation

Phase 8 is verified by:

- unit tests for terminology mining
- unit tests for entity linking
- unit tests for domain autonomy and domain intelligence surface
- acceptance tests for KB import
- acceptance tests for domain-linked query scoring
- acceptance tests for autonomous domain adaptation and domain studio surface
- storage contract regression coverage
