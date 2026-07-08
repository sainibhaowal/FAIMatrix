## Phase B: Weighted Expansion Engine

### Status

Implemented and validated.

### Why this phase exists

Before this phase, FAIM had real query expansion, but it was still shallow:

- ConceptNet expansion mainly behaved like flat synonym appending
- canonical semantics and multilingual normalization produced useful additive text, but not a shared weighted expansion surface
- domain lexicon matches were used for candidate linking, but not fully blended into the same lexical expansion path

That meant FAIM had good deterministic recall, but not yet a unified production-grade expansion engine.

### What changed

Phase B upgrades query-time lexical expansion into a deterministic weighted engine built from four real sources:

1. ConceptNet token and phrase expansions
2. graph-local canonical semantics
3. multilingual concept/translation mappings
4. graph-local domain lexicon expansions

All expansions are:

- capped
- weighted
- source-tagged
- merged deterministically
- rendered additively without changing the public query API

### Files implemented

- [synonym_expander.py](/home/sephi-asi/FAIM/faim_native/lexical/synonym_expander.py)
- [canonicalizer.py](/home/sephi-asi/FAIM/faim_native/lexical/canonicalizer.py)
- [multilingual_canonicalizer.py](/home/sephi-asi/FAIM/faim_native/lexical/multilingual_canonicalizer.py)
- [query_flow.py](/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py)
- [test_weighted_expansion_engine.py](/home/sephi-asi/FAIM/tests/unit/test_weighted_expansion_engine.py)
- [test_AT_CAN2_query_canonical_semantics.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_CAN2_query_canonical_semantics.py)
- [test_AT_ML2_cross_lingual_query.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_ML2_cross_lingual_query.py)

### Runtime behavior now

When a user asks a query:

1. FAIM canonicalizes the query with graph-local canonical semantics
2. FAIM extracts weighted canonical expansions from lemma and phrase matches
3. FAIM adds weighted ConceptNet token and phrase expansions
4. FAIM adds weighted multilingual concept and translation expansions
5. FAIM adds weighted domain-lexicon expansions learned from the current graph
6. FAIM merges all expansions into one deterministic ranked set
7. FAIM caps the expansion set and renders additive expanded query text
8. The existing vector, Representation V2, graph, and reranker path runs on that stronger query surface

### What stayed unchanged

- `v_native` remains the canonical vector spine
- query result shape was not widened
- graph expansion and deterministic reranker contracts stay intact
- exact fallback behavior stays intact
- tenant isolation and graph scoping stay intact
- no ML or transformer dependency was introduced

### Explainability

When query explain mode is enabled, FAIM now returns a Phase B block that includes:

- base query text
- canonical query text
- final expanded query text
- source counts
- expansion rows with:
  - term
  - weight
  - sources
  - origins

This keeps the stronger recall path inspectable instead of turning it into hidden heuristics.

### Validation completed

Validated with:

- [test_weighted_expansion_engine.py](/home/sephi-asi/FAIM/tests/unit/test_weighted_expansion_engine.py)
- [test_multilingual_canonicalizer.py](/home/sephi-asi/FAIM/tests/unit/test_multilingual_canonicalizer.py)
- [test_AT_CAN2_query_canonical_semantics.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_CAN2_query_canonical_semantics.py)
- [test_AT_ML2_cross_lingual_query.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_ML2_cross_lingual_query.py)
- [test_cortex_runtime.py](/home/sephi-asi/FAIM/tests/unit/test_cortex_runtime.py)
- [test_AT_CORTEX_turn.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_CORTEX_turn.py)

### Production verdict

Phase B is now real.

This does not yet replace the need for later phases like native late interaction or broader multilingual scale work, but it does complete the weighted expansion layer in a truthful, production-safe, FAIM-native way.
