# 92 - FAIM Semantic Signature V1 Report

## Status

Implemented.

## What this phase adds

Semantic Signature V1 extends the existing additive `RepresentationV2` sidecar
without changing the canonical `v_native` contract.

It adds deterministic semantic-style channels:

- `semantic_phrase_counts`
- `concept_counts`
- `morphology_counts`
- `alias_families`
- `transliterated_tokens`
- `stem_families`
- `relation_cues`
- `value_cues`
- `temporal_cues`

## Why this exists

FAIM already had:

- native hashed n-gram vectors
- phrase / skip / entity / time / layout sidecars
- graph expansion
- deterministic reranking

This phase strengthens fuzzy lexical-semantic matching while staying fully
FAIM-native and model-free.

## Runtime behavior

The new channels are:

- additive
- graph-scoped through existing `node_repr_v2` and `graph_repr_v2_stats`
- deterministic
- explainable
- safe to ignore if a caller only relies on `v_native`

Existing retrieval still works exactly as before. These channels only provide
extra recall and rerank signal when `RepresentationV2` is present.

## Query-time effect

At query time, the existing flow already builds `query_repr_v2` and asks
`RepresentationRepo` for lexical scores. After this phase, those lexical scores
also include Semantic Signature V1 channels.

The result is stronger matching for:

- abbreviations and aliases
- stem-family overlap
- transliterated multilingual surface forms
- relation-bearing language
- numeric / temporal phrasing
- phrase-level semantic structure

## User-visible effect

No new dedicated page was required for this phase.

Users will mainly notice:

- better retrieval for fuzzy wording
- better matching for alias-heavy queries
- better cross-lingual lexical bridging
- better explain/debug output when `return_explain=true`

Explain payloads now include a `semantic_signature` section summarizing the new
channels for each result node.

## Files

- `faim_native/encoding/semantic_signature.py`
- `faim_native/encoding/representation_v2.py`
- `faim_native/core/query/lexical_scorer.py`
- `faim_native/core/query/query_engine.py`
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/repos/representation_repo.py`
- `faim_native/store/pg/migrations/0030_semantic_signature_v1.sql`
- `faim_native/store/pg/schema.sql`

## Validation

Covered by:

- `tests/unit/test_semantic_signature.py`
- `tests/unit/test_representation_v2_determinism.py`
- `tests/unit/test_lexical_scorer.py`
- `tests/unit/test_representation_repo.py`
- `tests/acceptance/test_AT_RV2_representation_query.py`
- existing Cortex, multilingual, reranker, and no-ML validation suites
