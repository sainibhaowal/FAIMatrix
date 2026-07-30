# Benchmark Specification (Publication)

Version: faim-bench-publication-v1
Date: 2026-04-20

## Scope
- Track A (BEIR): SciFact, NQ, HotpotQA, FEVER, MS MARCO
- Track B: persistent memory behavior
- Track C: long-horizon continuity
- Track D: efficiency
- Track E: agent & API workflow
- Track F: real-world tasks
- BM-1..BM-9: system property checks
- Head-to-head baselines: BM25 chunk-RAG, dense RAG (all-MiniLM), summary memory
- Competitor slots: Mem0, Zep, SuperMemory, full-context GPT-4o 128k
- Native system: FAIM-Native
- Optional embedding baseline: sentence-transformers/all-MiniLM-L6-v2

## Metrics
- Retrieval: Recall@1/3/5/10, Precision@1/3/5/10, nDCG@1/3/5/10, MRR, MAP
- Publication table metrics: Recall@5, nDCG@10, MRR, MAP, task completion rate
- Confidence intervals: bootstrap 95% CI over per-query metric values

## Run Rules
- Same datasets and query/qrels sets for all systems
- Same top-k retrieval depth (20)
- Same metric implementation for all systems
- Same seed (42) for CI bootstrap
- Unrun competitor slots must show "skipped" or "—" in UI

## Hyperparameters
- k_values: [1, 3, 5, 10]
- retrieval_depth: 20
- confidence_bootstrap_iterations: 300
- seed: 42

## Integrity and Safety
- Tenant isolation is preserved through standard FAIM context
- Publication output is append-only event persisted via FAIM_BENCH_PUBLICATION_RESULT
- No core engine mutation required
