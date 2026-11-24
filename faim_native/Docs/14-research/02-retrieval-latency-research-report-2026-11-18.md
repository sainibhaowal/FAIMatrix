# FAIM Retrieval and Latency Research Report

**Prepared:** 2026-11-18
**Scope:** FAIM and FAIM-Native retrieval, memory, benchmark methodology, production readiness, and competitive gap
**Evidence cutoff:** repository state and retained benchmark artifacts inspected on 2026-11-18

## Executive conclusion

FAIM is not currently production-ready as a competitive retrieval system. The main blocker is not ingestion reliability or the absence of a graph; it is retrieval effectiveness combined with an unbounded query path.

The retained full SciFact run completed all 5,183 document ingests and all 300 queries with zero ingest errors, but FAIM-Native scored **0.0517 nDCG@10** while the same harness scored the BM25 reference **0.6644**. FAIM query latency was **17,373 ms p50** and **21,386 ms p95**, versus **35 ms p50** and **65 ms p95** for BM25. The FAIM/BM25 p50 latency ratio is approximately **495x**. The confidence intervals do not overlap for the principal retrieval metrics.

This is strong evidence that the current ranking pipeline is not retrieving relevant scientific abstracts reliably. It is not evidence that the whole FAIM product is broken: storage, ingestion, API readiness, and benchmark execution did work in this run. It is also not evidence that FAIM can never compete. It means FAIM needs a new measured retrieval foundation before graph reasoning, evolution, or additional UI features can support a market-level claim.

> Make retrieval quality and latency independently measurable first; use graph, evolution, and memory features only after a strong lexical/dense candidate set exists.

## 1. What was actually verified

### 1.1 External benchmark result

Source: Historical `v9` baseline run `ret_scifact_20261117T214211Z_ccef064a` (retained metrics; superseded by [`scifact-v19-ready`](../../../faim-benchmarks/results/gpu/scifact-v19-ready/ret_scifact_20261122T124757Z_df5d93fc.md)).

| Measure | FAIM-Native | BM25 reference | Interpretation |
|---|---:|---:|---|
| Recall@5 | 0.0539 | 0.7193 | Very few relevant documents appear in FAIM's first five results |
| Recall@10 | 0.0622 | 0.7816 | The gap remains large at the top-10 cutoff |
| nDCG@10 | 0.0517 | 0.6644 | Ranking quality is far below the lexical reference |
| MRR | 0.0535 | 0.6366 | The first relevant result is usually not near the top for FAIM |
| MAP | 0.0467 | 0.6242 | Overall relevant-result ordering is weak |
| Query p50 | 17,373 ms | 35 ms | FAIM is approximately 495x slower in this run |
| Query p95 | 21,386 ms | 65 ms | Tail latency is approximately 328x slower |
| Ingest errors | 0 | 0 | The result is not explained by failed ingestion |
| Queries evaluated | 300 | 300 | Both systems used the complete retained SciFact test query set |

Bootstrap 95% intervals are retained in the artifact. For example, FAIM nDCG@10 is [0.0303, 0.0743] and BM25 is [0.6194, 0.7122]; this is not a small random fluctuation around parity.

### 1.2 Benchmark integrity status

The harness is useful and honest, but this artifact is not yet a clean release claim:

- It uses the official BeIR SciFact corpus and test qrels: 5,183 documents and 300 queries.
- The same query set, qrels, top-k, scorer, and bootstrap method were used for FAIM and BM25.
- The run metadata records faim_profile=fast, Phase 5 enabled, Representation V2 enabled, and self-evolution disabled.
- The artifact records git_worktree_dirty=true and a benchmark commit different from the current repository HEAD.
- The publication gate is explicitly NOT READY because the worktree was dirty.
- The artifact does not record the exact active embedding provider and model revision. The retained graph has 384-dimensional embeddings, and the current repository contains a 384-dimensional IBM Granite local model, but that is not sufficient to prove which model produced the historical run.

The run is valid evidence about the executed configuration. It is not yet a clean-HEAD, model-pinned release benchmark.

### 1.3 Runtime readiness checks

The current API readiness check returned:

    {"status":"ready","db_connected":true,"tables_ok":true,"migrations_ok":true,"latest_migration":43,"applied_migration":43}

The inspected Docker deployment was running API, frontend, PostgreSQL, Qdrant, Redis, and worker services. The current container configuration included embedding prewarm, indexing, Phase 5, and Representation V2. These are operational facts, not evidence of retrieval quality.

### 1.4 Retained graph data audit

The retained SciFact graph was inspected read-only:

- 5,213 nodes, 5,213 dense embeddings, and 5,213 raw references.
- 5,213 Representation V2 rows, with normalized rows present.
- Dense vector dimension: 384.
- Normalized text length: minimum 35 characters, median approximately 1,427, maximum 4,872, p95 approximately 2,418.
- All retained nodes are below the current 5,000-character extraction threshold, so this run did not exercise large-document splitting.
- Edge counts included approximately 41,668 inheritance edges, 41,573 synonym edges, 5,170 opposition edges, 74 hypernym edges, and 21 related edges.

The 30-node difference between 5,213 nodes and 5,183 source documents requires a reproducibility explanation. It may be expected derived or duplicate graph material, but it must be accounted for before publishing a corpus-to-node coverage claim.

## 2. Why the benchmark is so bad

The following diagnosis separates observed facts from engineering hypotheses.

### 2.1 The observed failure is ranking, not ingestion

Because all 5,183 documents were ingested and all 300 queries completed, the first question is not “did FAIM receive the data?” It did. The first question is “did the candidate generator place relevant documents in a recoverable set, and did the reranker preserve them?” The scores indicate one or both stages are failing.

The current artifact does not retain per-query retrieved IDs, candidate recall at 100/200, score components, or stage timings. Consequently, the exact split between candidate-recall loss and reranking loss is not yet proven. This is the first measurement gap to close.

### 2.2 FAIM's native representation is not a learned scientific retriever

faim_native/encoding/text_vectorizer.py describes a deterministic 256-dimensional hashed character n-gram representation with hand-engineered statistics. It contains no pretrained language model. This is useful for deterministic local behavior, but it does not provide the semantic representation learned from scientific paraphrases, terminology, abbreviations, and claim/evidence relationships that SciFact requires.

The query path may additionally use a 384-dimensional embedding provider, but the benchmark artifact does not identify the provider, model revision, pooling method, or normalization contract. A generic or incorrectly configured embedding model can fail on scientific claims even when its vector API is functioning.

**Implication:** deterministic expansion and graph scoring cannot substitute for a strong, version-pinned first-stage scientific retriever.

### 2.3 The system performs many expensive stages before returning results

The current query flow performs query expansion, IDF work, inheritance expansion, graph metrics, version lookup, cache lookup, Phase 5 sparse and dense recall, lexical scoring, multi-hop graph diffusion, optional embedding encoding, semantic embedding recall, FAIM reranking, event emission, usage-touch updates, and result construction.

The code is feature-rich, but the retained p50 of 17.4 seconds shows that this path is not bounded tightly enough. The code also preserves fallback branches that can rescan representations or use broader graph/SQL paths when an index stage is unavailable.

The benchmark proves the end-to-end latency outcome. It does not yet prove which stage consumes the time. Stage-level tracing is required before optimization claims are made.

### 2.4 Graph expansion can amplify a weak seed set

Graph reasoning is valuable when the initial nodes are relevant and the edge semantics are trustworthy. If the first-stage candidate set is wrong, multi-hop inheritance, synonym, opposition, and diffusion can add related-but-not-relevant nodes and displace true evidence. This is a likely failure mode, not a proven causal attribution.

The safe ordering is:

1. retrieve a high-recall lexical/dense candidate set;
2. preserve the lexical/dense candidates;
3. use graph features as a bounded reranking or expansion signal;
4. measure whether graph features improve or reduce nDCG and recall in an ablation.

Graph features must never silently reduce candidate recall.

### 2.5 Document granularity is too coarse for evidence reasoning

SciFact relevance is annotated at the abstract/document level, so whole-abstract ingestion is not an unfair shortcut for this retrieval metric. However, FAIM's current extraction path stores most SciFact records as one EvidenceBlock. That makes exact rationale selection and later cross-encoder or late-interaction reranking harder.

This is probably a secondary cause of the current document-retrieval gap, not the primary explanation. The first fix is a better retriever and candidate diagnostics; sentence/paragraph evidence blocks should follow.

### 2.6 The pipeline is not ablated

The run turns on multiple interacting features: Phase 5, Representation V2, IDF, inheritance expansion, graph semantic diffusion, optional embeddings, and FAIM reranking. Without an ablation matrix, the project cannot know whether a feature helps, is neutral, or is actively damaging retrieval.

| Variant | Purpose |
|---|---|
| BM25 only | lexical reference and latency target |
| Native 256-d only | measure deterministic FAIM representation |
| Dense embedding only | measure the active embedding model independently |
| BM25 + dense fusion | test a standard hybrid baseline |
| Hybrid + FAIM reranker | quantify reranker contribution |
| Hybrid + graph rerank | quantify graph contribution |
| Full pipeline | measure whether the complete system helps or hurts |

Each row needs quality, candidate recall, stage timings, memory use, and error counts.

## 3. What current retrieval research says FAIM is missing

The current research baseline is not one magical model. It is a measured multi-stage architecture.

### 3.1 A strong lexical baseline is mandatory

The BEIR paper found BM25 to be a robust zero-shot baseline across heterogeneous retrieval datasets. It also reported that late-interaction and reranking methods can achieve stronger quality at higher computational cost, while dense and sparse neural retrievers trade quality and efficiency differently. This is directly relevant: FAIM currently loses to BM25 on its own retained SciFact run, so a production path must first include and preserve a strong lexical leg.

Source: [BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663).

### 3.2 Dense retrieval needs a task-appropriate encoder

A single-vector dense encoder can improve semantic matching, but only if it is trained or validated for the task and the model contract is pinned. The report should record model name, revision/hash, tokenizer, pooling, normalization, dimensionality, device, batch size, and whether the query and document encoders are symmetric.

For scientific retrieval, a general-purpose embedding score must be treated as a hypothesis until measured on SciFact and adjacent scientific datasets such as NFCorpus and SciDocs.

### 3.3 Learned sparse retrieval is a credible middle path

SPLADE-style learned sparse representations preserve inverted-index behavior while adding learned lexical expansion. That is relevant to FAIM because it can improve terminology mismatch without forcing every query through a full dense/graph pipeline.

Source: [SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking](https://arxiv.org/abs/2107.05720).

### 3.4 Late interaction and reranking are separate quality layers

ColBERTv2 represents queries and documents with multiple token-level vectors and uses late interaction rather than collapsing each text into one vector. Its paper reports strong retrieval quality with compression improvements. PLAID describes an optimized late-interaction engine that reduces search latency through centroid pruning and reports tens of milliseconds on GPU and tens to a few hundreds of milliseconds on CPU at the evaluated scales.

Sources: [ColBERTv2](https://arxiv.org/abs/2112.01488) and [PLAID](https://arxiv.org/abs/2205.09707).

FAIM does not currently have a measured, independently validated cross-encoder or late-interaction baseline in the public artifact. A deterministic “late interaction” feature is not equivalent to a learned late-interaction retriever unless it is evaluated as one.

### 3.5 ANN indexing must have a measured recall/latency trade-off

Vector indexes are not automatically fast or accurate. FAISS frames vector search as a trade space involving indexes, transformations, compression, and interfaces. Qdrant documents HNSW and filterable HNSW as approximate-nearest-neighbor mechanisms with a measurable recall cost and payload-index support.

Sources: [The Faiss library](https://arxiv.org/abs/2401.08281), [Qdrant HNSW documentation](https://qdrant.tech/course/beginners/module-2/hnsw/), and [Qdrant filtering documentation](https://qdrant.tech/documentation/search/filtering/).

FAIM currently has a deterministic ANN/Phase 5 path, but the public report does not show ANN recall against exact search, index build time, candidate recall@100/200, or latency by stage. Those are required before calling the index production-grade.

## 4. Competitor comparison: what is and is not comparable

FAIM has been discussed beside Mem0, Zep, Supermemory, and Letta. Those products mainly publish agent-memory or context-engineering evaluations, while the retained FAIM result is a document-retrieval benchmark on SciFact. The numbers cannot be placed on one leaderboard without matching dataset, split, scorer, answer model, prompt, aggregation policy, and cost/latency measurement.

| System/category | Public evidence | What it demonstrates | Why it is not a direct FAIM comparison |
|---|---|---|---|
| Mem0 | [Mem0 paper](https://arxiv.org/abs/2504.19413), [official research page](https://mem0.ai/research) | Long-horizon conversational memory, extraction, retrieval, and graph-memory variants | LoCoMo/LongMemEval-style memory tasks, not SciFact abstract retrieval |
| Zep | [Zep paper](https://arxiv.org/abs/2501.13956), [benchmark page](https://www.getzep.com/research/memory-benchmarks/) | Temporal knowledge-graph memory and long-running agent recall | Different tasks, answer protocol, model, and temporal-memory requirements |
| Supermemory | [official research page](https://supermemory.ai/research/) | Published LongMemEval-S and conversational-memory results | Vendor-reported memory protocol; not the same document-retrieval scorer |
| Letta | [Context-Bench](https://www.letta.com/blog/context-bench/) | Stateful-agent context engineering and tool/file behavior | Agent trajectory evaluation, not a fixed SciFact IR test |
| BM25 | Same FAIM artifact | Strong, simple lexical reference on the exact FAIM test | It is the only directly comparable completed reference in the retained run |

The correct competitive statement today is not “FAIM beats these systems.” It is:

> FAIM has not yet published a matched, reproducible head-to-head against those memory systems, and on its completed SciFact retrieval run it is substantially behind its own BM25 reference in both quality and latency.

The next fair comparison is to run each system through one locked suite per task family: SciFact/BEIR for document retrieval, and LoCoMo/LongMemEval for agent memory. Published competitor numbers can be listed as context, but they must remain explicitly non-comparable until the protocol is matched.

## 5. Missing technology and engineering capabilities

### Retrieval quality

1. A version-pinned scientific dense retriever or a validated general retriever.
2. A BM25 or learned-sparse inverted-index leg that cannot be displaced by graph noise.
3. Hybrid fusion with an explicit method such as reciprocal-rank fusion or calibrated weighted fusion.
4. A learned reranker or late-interaction model over a bounded top-50/top-100 candidate set.
5. Sentence/paragraph evidence blocks with document-level aggregation for rationale and citation support.
6. Training or validation data for scientific claims, terminology, and hard negatives.
7. Per-query retrieval diagnostics: candidate recall, rank of first relevant item, source leg, score components, and failure class.

### Latency and scale

1. Stage-level tracing for encode, lexical retrieval, ANN retrieval, graph expansion, rerank, database I/O, event writes, and response serialization.
2. A hard candidate budget and a single bounded query plan for the fast profile.
3. Precomputed document representations and query-embedding batching.
4. ANN recall/latency calibration against exact search.
5. No synchronous full-graph or full-representation scans in the normal fast path.
6. Cache keys that include model revision, index revision, graph version, tenant, and query normalization version.
7. Separate read latency from usage-touch/event-journal writes, or make those writes asynchronous.
8. Concurrency, load, warm-cache, cold-cache, and failure-mode tests at the intended corpus sizes.

### Benchmark science

1. Clean Git commit and reproducible environment lock.
2. Exact dataset revisions, qrels, model artifacts, provider configuration, and hardware in every artifact.
3. Per-query outputs and stage timings retained as a machine-readable artifact.
4. Candidate recall@100 and recall@200 in addition to final nDCG@10.
5. Paired bootstrap or permutation comparisons for each material change.
6. Ablations for every major feature family.
7. Multiple public datasets; SciFact alone is not a market-wide retrieval claim.
8. Separate retrieval evaluation from answer-generation evaluation.

### Production operations

1. Model/index migration and rollback procedure.
2. Tenant isolation and permission filtering tested during retrieval, not only after retrieval.
3. Data deletion and update tests proving stale vectors and graph edges cannot surface.
4. Restore drills for PostgreSQL, Qdrant, Redis, model artifacts, and benchmark provenance.
5. SLO dashboards for quality, latency, error rate, queue depth, and cost.
6. Rate limits, backpressure, timeout budgets, circuit breakers, and degraded-mode behavior.
7. Security review for API keys, authorization, provider egress, document access, logs, and prompt/data egress.

## 6. Target architecture to close the gap

### Phase 0: measurement freeze

Before changing ranking logic:

- run from a clean commit;
- pin and record embedding/reranker model IDs and hashes;
- add per-query retrieved IDs and candidate IDs;
- add stage timings and counters;
- add candidate recall@100 and @200;
- add the ablation matrix above;
- account for the 30-node document-to-node difference;
- distinguish warm-cache and cold-cache latency.

**Exit gate:** every benchmark result is reproducible from the repository, environment lock, dataset revisions, and model manifest.

### Phase 1: strong first-stage retrieval

Implement and measure three independent legs:

1. BM25/inverted lexical search;
2. dense ANN search with a pinned encoder;
3. optional learned sparse search.

Fuse the legs using a simple, inspectable method. Keep the top 100–200 candidates before any graph or learned reranker.

**Exit gate:** candidate recall@100 is at least 0.95 on SciFact, with a documented trade-off between recall and latency. This is a target, not a current result.

### Phase 2: evidence granularity

Split documents into sentence/paragraph evidence blocks while preserving document IDs and section/offset metadata. Retrieve at block level, aggregate to document level for SciFact scoring, and expose the supporting sentence for downstream verification.

**Exit gate:** no loss in document recall, plus a measurable improvement in rationale/evidence selection.

### Phase 3: bounded learned reranking

Rerank only the top 50–100 candidates using a cross-encoder or late-interaction model selected through offline evaluation. The reranker must be optional and budgeted; it must not run over the whole graph.

**Exit gate:** nDCG@10 improves over the best first-stage baseline with a declared p95 budget.

### Phase 4: graph as a gated feature

Apply graph expansion only after the strong candidate set exists. Treat graph scores as a bounded reranking feature. Run graph-on versus graph-off on the same queries and keep graph enabled only where it improves paired metrics without violating latency or precision guardrails.

**Exit gate:** graph-on wins a predeclared paired test or is restricted to query classes where it wins.

### Phase 5: production performance

For an initial 5k–100k-document tenant target, establish engineering targets of **p50 below 200 ms and p95 below 500 ms** for retrieval-only queries, then scale-test beyond that size. These are design targets, not claims about the current system and not guarantees for every hardware/model configuration.

The fast path should be:

    normalize -> encode once -> lexical + ANN in parallel -> fuse -> bounded rerank -> return

Graph diagnostics, usage touches, journal writes, and optional answer synthesis should be asynchronous or separately budgeted unless the request explicitly asks for them.

### Phase 6: broad public evaluation

Use SciFact plus adjacent BEIR/MTEB retrieval tasks such as NFCorpus and SciDocs, then add an agent-memory suite such as LoCoMo and LongMemEval if FAIM claims memory functionality. Report per-dataset scores, confidence intervals, latency percentiles, hardware, model, cost, and failure rates. Do not average incompatible task families into one “intelligence score.”

## 7. Acceptance gates for a credible production claim

FAIM should not be labeled “production-ready retrieval” until all of the following are true:

| Gate | Required evidence |
|---|---|
| Correctness | Best retrieval configuration beats BM25 on nDCG@10 or clearly documents the task where it does not |
| Candidate recall | Recall@100 and @200 are measured and meet the predeclared target |
| Latency | Warm/cold p50, p95, and p99 measured under representative concurrency |
| Reproducibility | Clean commit, lockfile, model hashes, dataset revisions, hardware, and complete JSON artifact |
| Regression control | CI or release job rejects quality/latency regressions beyond thresholds |
| Data lifecycle | Update, delete, tenant isolation, and restore tests pass |
| Observability | Stage traces expose failures without logging secrets or document contents improperly |
| Security | Credential, authorization, provider-egress, and deletion controls are tested |
| Scope honesty | SciFact, BEIR, and memory benchmark claims are separated by task and protocol |

“Perfect” retrieval is not a defensible engineering claim. The defensible claim is that a specified system, on specified datasets and hardware, meets specified quality, latency, reliability, and reproducibility gates.

## 8. Recommended order of work

1. **Freeze evidence:** clean benchmark run, model manifest, per-query artifacts, candidate recall, and stage timing.
2. **Build the baseline ladder:** BM25, dense, hybrid, hybrid+reranker, then graph-on/off.
3. **Fix retrieval quality:** keep the best first-stage architecture and only then tune graph/evolution features.
4. **Fix latency:** remove unbounded scans and synchronous side effects; tune ANN and reranker budgets.
5. **Add scientific evidence granularity:** sentence/paragraph blocks and rationale support.
6. **Expand the benchmark suite:** SciFact plus other BEIR/MTEB datasets, then memory benchmarks separately.
7. **Run production qualification:** concurrency, failures, updates/deletes, security, restore, and cost.
8. **Publish only clean artifacts:** one release commit, signed JSON, exact command, model manifest, and limitations.

Do not spend the next iteration on visual polish, extra graph features, or market claims before steps 1–3 produce a strong retrieval baseline. Those additions cannot compensate for a first-stage system that currently loses to BM25 by more than twelve times on nDCG@10 and by roughly 495 times on p50 latency.

## 9. Current state versus required state

| Area | Current verified state | Required state |
|---|---|---|
| API/storage | Ready endpoint and migrations pass in the inspected deployment | Add SLO, failure, restore, and multi-tenant qualification |
| Ingestion | Full SciFact ingestion completed with zero errors | Preserve provenance, update/delete correctness, and coverage accounting |
| Native representation | Deterministic 256-d hashed n-gram vector | Keep as a fallback/feature, but add validated scientific dense/sparse retrieval |
| Dense model | 384-d vectors exist in retained graph; historical provider not recorded | Pin model/provider/hash and publish manifest |
| Granularity | Mostly one EvidenceBlock per SciFact abstract | Sentence/paragraph evidence blocks with document aggregation |
| Candidate recall | Not retained in public artifact | Measure and gate recall@100/@200 |
| Ranking quality | FAIM nDCG@10 0.0517 versus BM25 0.6644 | Meet or exceed the best reference on declared datasets |
| Query latency | 17.4 s p50, 21.4 s p95 | Establish bounded sub-second retrieval target under load |
| Graph/evolution | Feature-rich graph path; self-evolution disabled in canonical run | Gate graph by measured ablations; qualify evolution separately |
| Benchmark release | Honest but dirty-worktree, model metadata incomplete | Clean, pinned, independently reproducible release artifact |
| Competitor claims | Published external numbers are non-comparable context | Matched protocol runs or clearly labeled contextual references |

## 10. Limitations of this report

- The retained benchmark contains aggregate metrics and bootstrap intervals, not complete per-query rankings or stage traces; exact failure attribution remains unresolved until those are added.
- The historical active embedding provider/model is not fully recorded in the artifact.
- Only BM25 was completed as a direct comparator in the retained public run; Mem0, Zep, Supermemory, and Letta were not executed under the same protocol.
- Published vendor memory results use different tasks, models, prompts, and scoring. They are useful for capability mapping, not direct ranking against FAIM's SciFact score.
- The latency targets in this document are engineering goals for a defined workload, not achieved measurements.
- This report evaluates retrieval and production evidence. It does not certify legal compliance, security certification, or a guarantee of market success.

## Sources and reproducibility links

### Local evidence

- Superseded `v9` baseline metrics preserved in Section 1.1 (`ret_scifact_20261117T214211Z_ccef064a`); current canonical results are in [`RESULTS.md`](../../../faim-benchmarks/results/RESULTS.md)
- [Benchmark harness README](../../../faim-benchmarks/README.md)
- [FAIM query flow](../../orchestration/query_flow.py)
- [FAIM native text vectorizer](../../encoding/text_vectorizer.py)
- [FAIM ingestion flow](../../orchestration/ingest_flow.py)
- [Embedding provider registry](../../encoding/embedding_providers.py)

### Primary external research and technical references

- [Fact or Fiction: Verifying Scientific Claims: SciFact](https://aclanthology.org/2020.emnlp-main.609/)
- [BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663)
- [SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking](https://arxiv.org/abs/2107.05720)
- [ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction](https://arxiv.org/abs/2112.01488)
- [PLAID: An Efficient Engine for Late Interaction Retrieval](https://arxiv.org/abs/2205.09707)
- [The Faiss library](https://arxiv.org/abs/2401.08281)
- [Qdrant HNSW documentation](https://qdrant.tech/course/beginners/module-2/hnsw/)
- [Qdrant filtering documentation](https://qdrant.tech/documentation/search/filtering/)
- [LongMemEval](https://arxiv.org/abs/2410.10813)
- [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413)
- [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)
- [Supermemory research](https://supermemory.ai/research/)
- [Letta Context-Bench](https://www.letta.com/blog/context-bench/)
