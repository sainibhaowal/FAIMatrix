# FAIM Retrieval Improvement: MoSCoW Requirements and Safe Implementation Plan

**Status:** implementation in progress
**Branch:** feature/faimatrix-retrieval-production-foundation
**Owner:** FAIM repository maintainers
**Decision:** retrieval quality and bounded latency are the release-critical workstream

## 1. What to do

Build a measured retrieval ladder without disturbing the existing FAIM product contract:

1. Freeze benchmark provenance and per-query evidence.
2. Establish independent BM25, dense, hybrid, reranker, and graph ablations.
3. Measure candidate recall separately from final ranking quality.
4. Bound the fast query path and expose stage-level latency.
5. Add evidence granularity and document aggregation.
6. Gate graph/evolution features by measured quality and latency.
7. Qualify security, tenant isolation, updates, deletes, restores, concurrency, and regressions.
8. Publish only clean, model-pinned, reproducible artifacts.

This plan intentionally begins with measurement and release hygiene. Ranking logic is not changed until the failure stage is observable.

## 2. Why it is required

The retained full SciFact run completed ingestion but scored FAIM nDCG@10 at 0.0517 versus BM25 at 0.6644, with FAIM query p50 at 17,373 ms versus 35 ms. The current result proves an effectiveness and latency gap. It does not identify whether candidate recall, reranking, graph expansion, embedding configuration, database work, or synchronous side effects are responsible.

Changing many ranking features before capturing this evidence would make the system harder to debug and could damage existing behavior. The first implementation therefore adds safe diagnostics to the external benchmark harness and makes the next run scientifically actionable.

## 3. What already exists

- Public HTTP benchmark adapter in faim-benchmarks/faim_benchmarks/adapters/faim_http.py.
- Reproducible BEIR loader in faim-benchmarks/faim_benchmarks/datasets.py.
- BM25 reference adapter in faim-benchmarks/faim_benchmarks/adapters/competitors.py.
- IR metrics and bootstrap intervals in faim-benchmarks/faim_benchmarks/metrics.py.
- Signed JSON and Markdown artifacts in faim-benchmarks/faim_benchmarks/report.py.
- Benchmark orchestration in faim-benchmarks/faim_benchmarks/runner.py.
- CLI and runtime metadata in faim-benchmarks/faim_benchmarks/cli.py.
- Existing API route POST /api/v1/ingest.
- Existing API route POST /api/v1/query.
- Existing QueryResponse metrics including Phase 5 candidate counts, cache status, and degraded-feature count.
- Existing FAIM query path, Representation V2, Phase 5, deterministic ANN, optional embedding provider, graph expansion, reranking, events, and touch updates.
- Existing Docker services, authentication middleware, tenant headers, database, Qdrant, Redis, worker, frontend, memory, storage, evolution, MCP, OAuth, and journal surfaces.
- Existing benchmark artifact and research report documenting the current gap.

## 4. MoSCoW requirements

### MUST: release-critical

| Requirement | Why | Exact implementation area | Acceptance evidence |
|---|---|---|---|
| Retain per-query IDs, qrels, metrics, and latency | Find candidate/ranking failures | benchmark runner, adapter outcome | Signed JSON contains traces and no text |
| Record model/provider/revision metadata | Make results reproducible | benchmark CLI metadata | Artifact contains non-secret model manifest |
| Keep benchmark clean-commit gate | Prevent false publication | report publication gate | Dirty or incomplete runs remain NOT READY |
| Preserve BM25 baseline | Prevent regression against the simplest reference | BM25 adapter and runner | Existing and new harness tests pass |
| Add ablation entry points | Attribute quality changes | benchmark CLI/system selection and future adapters | Each variant has an independent result |
| Measure warm/cold and stage latency | Find the 17-second bottleneck | API telemetry and benchmark harness | p50/p95/p99 and stage fields are retained |
| Keep auth and tenant headers unchanged | Protect isolation | FaimHttpAdapter only | Auth/tenant tests and API acceptance tests pass |
| Avoid query/document text in trace artifacts | Prevent data leakage | QueryOutcome and report writer | Negative test proves text is absent |
| Test update/delete/tenant isolation | Prevent stale or cross-tenant retrieval | API/storage/query integration tests | Explicit pass/fail evidence |

### SHOULD: high-value next

| Requirement | Why | Exact implementation area | Acceptance evidence |
|---|---|---|---|
| Dense ANN baseline with pinned encoder | Semantic retrieval | embedding provider and benchmark adapter | Model hash, recall, latency, CI |
| BM25 + dense hybrid fusion | Robust lexical/semantic recall | benchmark adapter or query strategy | Hybrid beats both component baselines |
| Candidate recall@100/@200 | Separate recall from reranking | query response/diagnostic contract | Measured against qrels |
| Bounded reranker top-50/top-100 | Improve ranking without whole-graph cost | query orchestration/reranker service | nDCG gain within p95 budget |
| Sentence/paragraph evidence blocks | Improve rationale and reranking | extractors and ingest flow | Document recall does not regress |
| Async journal/touch side effects | Reduce read latency | query flow and event/journal services | Retrieval latency excludes or bounds writes |
| Multi-dataset BEIR/MTEB suite | Avoid SciFact-only claims | benchmark CLI/datasets | Results for SciFact, NFCorpus, SciDocs |

### COULD: after the baseline wins

| Requirement | Why | Exact implementation area | Acceptance evidence |
|---|---|---|---|
| Learned sparse retrieval | Learned terminology expansion | standalone benchmark adapter | Quality/latency/cost comparison |
| Late interaction retrieval | Stronger passage matching | standalone bounded adapter/service | Reproducible ColBERT-style result |
| Graph-gated reranking | Use FAIM differentiator safely | query flow graph scoring | Graph-on wins paired ablation |
| Evolution-aware index refresh | Keep indexes current | evolution flow/worker/index rebuild | No stale or partial index exposure |
| LoCoMo/LongMemEval qualification | Validate memory claims | memory adapters and runner | Separate memory report |
| Cost and energy reporting | Production trade-offs | benchmark metadata | Hardware/cost assumptions retained |

### WON'T: out of scope until retrieval gates pass

- Claim perfect retrieval or universal market superiority.
- Replace the existing auth, tenant, cryptography, or provider credential model.
- Rewrite the frontend or remove existing storage, memory, evolution, MCP, OAuth, or journal routes.
- Delete current APIs or change their request/response contracts without a versioned migration.
- Enable self-evolution automatically in a benchmark used for release claims.
- Mix vendor-reported memory scores with SciFact retrieval scores.
- Commit local credentials, downloaded corpora, database dumps, model weights, or resources/.

## 5. Exact paths, routes, APIs, schemas, tests, and docs

### Current benchmark surface

- faim-benchmarks/faim_benchmarks/adapters/base.py: normalized IngestOutcome and QueryOutcome.
- faim-benchmarks/faim_benchmarks/adapters/faim_http.py: black-box FAIM HTTP calls and safe response diagnostics.
- faim-benchmarks/faim_benchmarks/adapters/competitors.py: BM25 and public competitor adapters.
- faim-benchmarks/faim_benchmarks/runner.py: dataset-wide execution, metrics, traces, failure isolation.
- faim-benchmarks/faim_benchmarks/report.py: signed artifact and publication gate.
- faim-benchmarks/faim_benchmarks/cli.py: command-line flags and non-secret run metadata.
- faim-benchmarks/faim_benchmarks/datasets.py: BEIR, LoCoMo, and LongMemEval loaders.
- faim-benchmarks/faim_benchmarks/metrics.py: IR/QA/latency metrics and bootstrap intervals.
- faim-benchmarks/tests/test_harness.py: deterministic harness, adapter, report, and failure-isolation tests.

### Existing FAIM runtime surface to protect

- faim_native/api/routers/query.py: POST /api/v1/query and QueryResponse.
- faim_native/api/routers/ingest.py: POST /api/v1/ingest.
- faim_native/api/routers/storage.py: storage uploads, files, and job status.
- faim_native/api/routers/auth.py and middleware/auth.py: authentication and tenant authorization.
- faim_native/api/routers/api_keys.py: API-key lifecycle.
- faim_native/api/routers/memory.py: memory write/search contracts.
- faim_native/api/routers/evolve.py and orchestration/evolve_flow.py: evolution contracts.
- faim_native/api/routers/events.py and store/journal/event_journal.py: event and journal behavior.
- faim_native/api/routers/mcp.py and oauth.py: MCP/OAuth integrations.
- faim_native/orchestration/query_flow.py: retrieval, graph, rerank, touches, and event lifecycle.
- faim_native/orchestration/ingest_flow.py and perception/extract/extractors_faim.py: extraction and block construction.
- faim_native/encoding/embedding_providers.py: provider registry and model loading.
- faim_native/index/: deterministic ANN/index artifacts.
- faim_native/store/pg/: persistence, tenant scope, migrations, and repositories.
- frontend/src/app/(admin)/dashboard/: existing operational UI.
- frontend/src/components/: existing storage, providers, evolution, graph, and journal components.

### Required test surfaces

- faim-benchmarks/tests/test_harness.py.
- tests/acceptance/test_AT_EV_B_evolve_status_surface.py.
- tests/acceptance/test_AT_storage* and storage/API-key/auth acceptance tests where present.
- tests/unit/test_mcp_oauth.py and existing security tests.
- API readiness and Docker smoke checks.
- New retrieval regression tests after ranking changes.

## 6. Safe implementation sequence

### Phase 0: measurement freeze

Current branch implementation:

- retain query traces as IDs, relevance IDs, metrics, latency, and safe adapter diagnostics;
- record model/provider/revision environment metadata;
- make publication gating stricter for retrieval artifacts;
- expose additive query-stage timings for candidate recall, graph expansion, embedding, reranking, answer synthesis, and total duration;
- support explicit nDCG, p95-latency, and FAIM-versus-BM25 release gates;
- preserve API requests, auth headers, tenant headers, and response mapping;
- add regression tests proving traces do not contain query or document text.

The FAST path now has a guarded relevance-first boundary. With Representation
V2 and Phase 5 enabled, Docker defaults to lexical-first fusion, skips the
graph-wide IDF scan, and skips broad graph expansion for FAST. This protects
query evidence and the latency budget; it is not a quality claim until a clean
matched benchmark confirms it. The switches are
`FAIM_FAST_RELEVANCE_FIRST`, `FAIM_FAST_GRAPH_EXPANSION`, and `FAIM_FAST_IDF`.
STRICT and BALANCED retain their existing graph and IDF behavior.

### Phase 1: baseline ladder

Implement each retrieval strategy behind an explicit strategy name. Do not replace the existing default query path yet.

1. BM25 exact reference.
2. Native deterministic vector.
3. Pinned dense embedding ANN.
4. BM25+dense reciprocal-rank fusion.
5. Bounded reranker.
6. Graph-on and graph-off ablation.

Every strategy must produce the same normalized result IDs and the same metric schema.

### Phase 2: evidence granularity

Add sentence/paragraph blocks with raw document ID, offsets, section, and block type. Keep document aggregation for current SciFact scoring. Add migration/reindex behavior only after update/delete and rollback tests exist.

### Phase 3: bounded query path

Add stage timers around encoding, lexical retrieval, ANN, graph expansion, reranking, database I/O, events, and touches. Set explicit budgets. Make nonessential writes asynchronous or separately measurable. Preserve degraded-mode behavior.

### Phase 4: graph/evolution gating

Run paired graph-on/off tests. Keep graph as a bounded reranking signal until it demonstrates a quality win without latency or precision regression. Keep self-evolution disabled for release benchmarks unless its exact state is recorded.

### Phase 5: production qualification

Run concurrency, warm/cold, scale, failure, restart, update, delete, restore, auth, tenant, and security tests. Publish only clean artifacts with model hashes and complete provenance.

## 7. What must not break

- Existing POST /api/v1/query and POST /api/v1/ingest contracts.
- Authorization, tenant isolation, API-key headers, bearer authentication, rate limits, and credential redaction.
- Encryption/cryptography code and secrets handling.
- Storage uploads, jobs, persistence modes, migrations, and graph versioning.
- Memory write/search adapters and idempotency behavior.
- Evolution triggers, worker scheduling, approvals, and rollback guards.
- Event journal ordering, query touch behavior, and observability.
- MCP and OAuth discovery/authentication.
- Frontend routes and existing user workflows.
- Docker service topology and health/readiness behavior.
- Existing benchmark failure isolation and explicit skipped competitor status.

## 8. Risks and controls

| Risk | Control |
|---|---|
| Traces leak text or secrets | Store only IDs, numeric metrics, bounded feature names, and whitelisted metadata |
| Benchmark changes query behavior | Benchmark adapter remains black-box and sends the same API contract |
| Dirty worktree contaminates commit | Feature branch and path-scoped staging; never stage unrelated files |
| Model drift invalidates comparison | Record provider/model/revision and reject incomplete release artifacts |
| Graph feature hurts recall | Graph-on/off paired ablation and candidate-recall gate |
| Reranker creates latency regression | Top-k budget and p95 release gate |
| Index migration loses data | Versioned rebuild, shadow index, rollback, and restore test |
| Tenant leakage | Cross-tenant query tests and authorization checks before performance tests |
| Existing dirty changes are overwritten | Never reset, checkout, clean, or restore unrelated paths |

## 9. Definition of done for the complete program

The program is complete only when:

1. The best declared retrieval strategy matches or beats BM25 on each declared task.
2. Candidate recall@100 and @200 are measured and meet target.
3. Warm/cold latency and representative concurrency meet the declared SLO.
4. Model, dataset, code, hardware, and environment provenance are complete.
5. Update/delete/tenant/restore/security tests pass.
6. Existing API, frontend, storage, memory, evolution, events, MCP, and OAuth regression suites pass.
7. The report and README describe only verified results.
8. Changes are committed on the feature branch and pushed only after all verification passes.
