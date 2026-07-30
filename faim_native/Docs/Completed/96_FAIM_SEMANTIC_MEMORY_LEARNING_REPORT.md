# Phase E: Semantic Memory Learning Report

## Status

Implemented in the FAIM-native domain-memory path.

## What changed

- FAIM now learns graph-local semantic bundles directly from uploaded graph content.
- The learner is deterministic, model-free, additive, and graph-scoped.
- The new learning path builds:
  - `concept_bundle` rows for learned graph-local concept groups
  - `semantic_paraphrase` rows for learned graph-local paraphrase members
  - `semantic_bundle` source records for traceable semantic bundle provenance
  - `semantic_bundle` graph edges between linked nodes that share a learned bundle
- Autonomous domain adaptation now merges these semantic-memory bundles into the existing domain lexicon instead of keeping them in a separate disconnected layer.
- Query-time domain expansion now reuses learned bundle members, so matching one learned surface can widen recall toward sibling paraphrases inside the same graph.
- Domain graph intelligence now renders bundle structure explicitly instead of showing only flat term rows.

## Safety properties

- Additive only: this does not replace `v_native`, representation-v2, weighted expansion, multilingual mapping, or deterministic reranking.
- Graph-scoped only: learned bundles stay inside the current graph.
- Deterministic only: no stochastic embedding model or external semantic classifier is introduced here.
- Explainable only: learned rows carry bundle metadata such as bundle key, members, shared context terms, and provenance source.
- Bounded only: learned terms, bundle count, bundle member count, and bundle graph edges are capped.

## Real effect on retrieval

Before Phase E:

- FAIM already mined graph-local domain terms, aliases, and fact-style structures.
- Query-time domain expansion could reuse those rows, but it did not yet learn stronger graph-local concept/paraphrase bundles from uploads themselves.

After Phase E:

- FAIM can learn that multiple graph-local surfaces belong to the same semantic neighborhood.
- Matching one learned surface can expand toward sibling bundle members during retrieval.
- Entity-linking and graph expansion can now reuse `semantic_bundle` edges as another graph-local signal.
- Domain Studio / domain intelligence can show bundle topology rather than only isolated terms.

## Files involved

- `faim_native/domain/semantic_memory.py`
- `faim_native/orchestration/domain_profile_rebuild.py`
- `faim_native/orchestration/query_flow.py`
- `faim_native/core/operators/entity_linking.py`
- `faim_native/domain/intelligence.py`
- `tests/unit/test_semantic_memory_learning.py`
- `tests/unit/test_domain_intelligence.py`
- `tests/unit/test_domain_autonomy.py`
- `tests/acceptance/test_AT_DK3_autonomous_domain_adaptation.py`

## Validation target

Phase E is complete when:

- uploads automatically produce graph-local semantic bundle learning
- learned bundle rows are persisted as domain lexicon rows
- learned bundle provenance is persisted as source rows
- linked graph nodes can be connected by semantic bundle edges
- query-time domain expansion can reuse learned bundle members
- domain intelligence surfaces learned bundles explicitly
