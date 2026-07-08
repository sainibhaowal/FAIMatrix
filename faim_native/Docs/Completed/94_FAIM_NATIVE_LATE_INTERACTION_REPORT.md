## Phase C: FAIM-Native Late Interaction

### Status

Implemented and validated.

### Why this phase exists

Phase B strengthened query expansion, but retrieval still needed a stronger
interaction layer between the query and each candidate document after recall.

Modern late-interaction systems get power from:

- keeping query-side units fine-grained
- matching them against document-side units cheaply
- aggregating those matches instead of depending only on one global vector score

FAIM now implements that idea in a native symbolic form.

### What changed

FAIM now has a new deterministic scorer in:

- [late_interaction_native.py](/home/sephi-asi/FAIM/faim_native/core/query/late_interaction_native.py)

This scorer does not use embeddings or token vectors. Instead it builds
query-side units from the existing FAIM-native representation and compares them
against document-side units using exact and bounded partial symbolic matching.

### Channels used

Phase C operates across:

- token units
- phrase units
- semantic phrase buckets
- concept buckets
- morphology buckets
- alias families
- transliteration bridges
- stem-family bridges
- relation cues
- value cues
- temporal cues

### Runtime integration

Phase C is wired into:

- [query_engine.py](/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py)
- [query_flow.py](/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py)

It runs:

1. after base FAIM scoring
2. after lexical, graph, modality, and domain additive signals
3. after the existing Phase 4 proposition/evidence reranker
4. before final deterministic ordering

This keeps the rollout safe:

- additive only
- no replacement of the existing ranker
- no change to `v_native`
- no change to result shape

### How it works

For each candidate document:

1. FAIM builds fine-grained query units from `RepresentationV2`
2. FAIM builds fine-grained document units from the candidate representation
3. Each query unit looks for its best document-side match
4. The best-match scores are aggregated channel by channel
5. Sparse count overlaps are blended for semantic phrase, concept, and morphology channels
6. A final bounded Phase C score is added into the reranking total

This is FAIM-native late interaction:

- no neural token matrix
- no MaxSim over learned embeddings
- symbolic MaxSim-style matching over deterministic lexical-semantic structures

### Explainability

When explain mode is enabled, FAIM now returns:

- `phaseC_late_interaction`

This includes:

- matched units by channel
- query unit counts
- per-channel score components in `score_components`

That means Phase C is inspectable in production and not hidden.

### Validation completed

Validated with:

- [test_late_interaction_native.py](/home/sephi-asi/FAIM/tests/unit/test_late_interaction_native.py)
- [test_reranker_v2.py](/home/sephi-asi/FAIM/tests/unit/test_reranker_v2.py)
- [test_AT_RR1_proposition_match.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_RR1_proposition_match.py)
- [test_cortex_runtime.py](/home/sephi-asi/FAIM/tests/unit/test_cortex_runtime.py)
- [test_AT_CORTEX_turn.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_CORTEX_turn.py)
- [test_AT_CAN2_query_canonical_semantics.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_CAN2_query_canonical_semantics.py)
- [test_AT_ML2_cross_lingual_query.py](/home/sephi-asi/FAIM/tests/acceptance/test_AT_ML2_cross_lingual_query.py)

### Production verdict

Phase C is real.

It does not try to imitate ColBERT with neural token embeddings. Instead, it
borrows the late-interaction principle and reimplements it as a deterministic
FAIM-native symbolic scorer that is safer, explainable, and additive to the
existing retrieval stack.
