# 76 - FAIM Query Life Cycle End-to-End Proof

## 1. Status
Completed for the current FAIM runtime contract.

FAIM now has a truthful layered query life cycle:

- deterministic Cortex task routing
- semantic broadening through ConceptNet, canonical semantics, multilingual
  bridges, domain memory, and semantic registry runtime
- retrieval through native vector, lexical, graph, and shortlist layers
- native late interaction and deterministic reranking
- bounded graph traversal with adaptive hop budgets
- `pulse-v2` proof surfaced in graph/query explain payloads and FIG View

## 2. End-to-end flow
1. **Input**
   - the user submits a query through Cortex chat or an API surface
2. **Task routing**
   - Cortex uses the compact deterministic task router to classify the turn
3. **Semantic broadening**
   - query flow applies weighted expansion from:
     - ConceptNet
     - canonical semantics
     - multilingual bridges
     - domain memory
     - semantic registry runtime
4. **Retrieval**
   - FAIM recalls candidates through native vector, lexical, graph, and
     shortlist layers
5. **Refinement**
   - native late interaction and deterministic reranker v2 strengthen the
     candidate set
6. **Traversal**
   - bounded graph traversal uses the planned adaptive hop budget where needed
7. **Pulse proof**
   - graph/query explain payloads emit the `pulse-v2` reason-source ledger used
     by FIG View to show node glow, path motion, inspector proof, relation
     traces, and semantic-layer contribution sources
8. **Answer**
   - Cortex returns the answer with provenance, retrieval, and reasoning state

## 3. Truthful example
Query:
`Why is the database failing?`

Truthful internal story:
- the task router can steer the turn toward contradiction or investigate style
  reasoning
- semantic expansion broadens terms like `database`, `failing`, and related
  graph vocabulary
- retrieval finds candidate evidence
- reranking and graph traversal sharpen the evidence set
- pulse-v2 explains which graph hops, expansion sources, semantic-registry
  matches, domain-memory links, reranker factors, and late-interaction signals
  contributed to visible FIG evidence
- the final answer is grounded in retrieved evidence and bounded traversal, not
  a fake single giant semantic-router step

## 4. What changed from the older story
Older wording compressed too much into one layer and implied:

- a `1M+ registry` performed direct reasoning-mode classification
- a fixed always-24-hop story

The truthful runtime is better:

- semantic registry runtime strengthens retrieval
- Cortex router selects the reasoning mode
- hop depth is adaptive and bounded, not blindly fixed
- FIG View reads a deterministic pulse-v2 ledger instead of relying on
  UI-only highlight guesses

## 5. Runtime truth
This end-to-end proof is real and aligned with the shipped runtime. It is not a
single monolithic registry step and it is not a fake fixed-hop claim.

## 6. Validation
Validated by:

- `python3 -m pytest tests/acceptance/test_AT_Q7_query_flow.py tests/acceptance/test_AT_semantic_fusion_determinism.py -q`
- `pnpm --dir frontend typecheck`

Current result:

- backend acceptance checks passed
- frontend typecheck passed

---

*Status: Completed and reconciled to runtime truth*
