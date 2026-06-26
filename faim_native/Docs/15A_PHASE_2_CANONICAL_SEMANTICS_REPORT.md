# 15A - Phase 2 Canonical Semantics Report

Phase 2 adds deterministic graph-local canonical semantics on top of FAIM-native retrieval.

Implemented:
- rule-based lemmatization
- acronym and alias mining
- phrase rewrite templates
- graph-scoped canonical term statistics
- graph-scoped canonical lexicon
- additive semantic edge kinds:
  - `distributional_synonym`
  - `paraphrase`
- storage rebuild route:
  - `POST /api/v1/storage/graphs/{graph_id}/canonical-semantics/rebuild`
- query-time canonical expansion using graph-local lexicon

Safety:
- `v_native` remains unchanged
- existing `vector_hash` and Representation V2 hashes remain unchanged
- canonical semantics rebuild is explicit and graph-scoped
- tenant and graph isolation are preserved in all new tables and queries

Mining rules:
- lemmatization is rule-based only
- aliases come from explicit acronym/alias text patterns
- distributional synonyms come from deterministic corpus counts:
  - support threshold
  - PMI threshold
  - context-overlap threshold
- paraphrase edges come from phrase-template normalization

New storage tables:
- `graph_term_stats`
- `graph_canonical_lexicon`

New semantic edge kinds:
- `distributional_synonym`
- `paraphrase`
