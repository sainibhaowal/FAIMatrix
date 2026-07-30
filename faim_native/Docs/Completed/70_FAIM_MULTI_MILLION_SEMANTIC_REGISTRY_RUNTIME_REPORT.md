# 70 - FAIM Multi-Million Semantic Registry Runtime Report

## 1. Overview
FAIM now has a **real semantic registry runtime** in the retrieval path. It is
not a fake fixed `1,048,576` concept-node lattice. It is a deterministic,
multi-source semantic lookup layer that merges:

- the embedded ConceptNet synonym archive
- the shipped multilingual lexicon packs
- graph-scoped canonical lexicon rows
- graph-scoped multilingual bridge rows
- graph-scoped domain-memory lexicon rows

This registry is active at query time through
[`faim_native/lexical/semantic_registry.py`](/home/sephi-asi/FAIM/faim_native/lexical/semantic_registry.py)
and is merged into the live expansion pipeline in
[`faim_native/orchestration/query_flow.py`](/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py).

## 2. What is real

### Static shipped base
- **ConceptNet synonym keys**: `2,172,991`
- **Static multilingual lexicon surfaces**: about `146,598`
- **Combined shipped registry term base**: about `2,319,589`

### Graph-local additive layers
These are not fixed global counts because they depend on uploaded data and
per-graph rebuilds:

- canonical semantics lexicon
- multilingual graph lexicon
- domain-memory lexicon

So the truthful claim is:

> FAIM has a **real 2.31M+ semantic registry term base**, with additional
> graph-local lexical memory layered on top at runtime.

## 3. What this registry is not
- It is **not** the tiny Cortex task router in
  [`faim_native/core/cortex/semantics.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/semantics.py)
- It is **not** a single TSV file
- It is **not** a fixed ontology with exactly `1,048,576` concept nodes
- It is **not** a hidden neural model

## 4. Runtime behavior
When a query arrives, FAIM now:
1. canonicalizes the query
2. broadens it with weighted ConceptNet expansions
3. adds multilingual bridges
4. adds graph-learned domain-memory expansions
5. resolves the same query through the new semantic registry runtime
6. merges all expansions deterministically and source-tags them
7. sends the expanded query into the existing FAIM retrieval, graph, reranker,
   and answer path

## 5. Explainability surface
In `return_explain=true` mode, the registry now shows up under:

- `phaseB_query_expansion.semantic_registry`

This includes:
- `registry_term_count`
- `conceptnet_terms`
- `static_lexicon_terms`
- `supported_languages`
- `matched_surface_count`
- `matched_surfaces`
- `expansion_count`

## 6. Determinism
The registry remains FAIM-native and deterministic:
- no stochastic rewrite model
- no opaque embedding router
- no external inference dependency
- stable merge order
- stable source tagging
- bounded expansion counts

## 7. Correct terminology
Use these phrases:
- **multi-million-term semantic registry runtime**
- **2.31M+ semantic registry term base**
- **combined registry-backed semantic expansion layer**

Do not use these phrases unless a separate exact ontology is later built:
- `1,048,576 semantic nodes`
- `1M exact concept nodes`
- `single giant semantic registry table`

---
*Status: Implemented and runtime-wired*
*Truthful shipped base: 2.31M+ semantic registry terms*
