# FAIM-Native documentation

This is the canonical documentation set for the code currently in this
repository. It is deliberately evidence-based: a document is included here
only when its claims can be mapped to the current source tree, Compose file,
frontend routes, or a reproducible test/evidence artifact.

## Current release posture

FAIM-Native has completed full **5,183-doc / 300-query `BeIR/scifact`** clean-tree
validation with **`Publication gate: READY`**:
[`scifact-v18-ready` (CPU)](../../faim-benchmarks/results/cpu/scifact-v18-ready/ret_scifact_20261122T001726Z_3a591ec9.md)
(`Recall@5 = 0.7554`, `nDCG@10 = 0.6878`, `MRR = 0.6570`, `MAP = 0.6464`,
`Query P50 = 231.07 ms`) and
[`scifact-v19-ready` (GPU)](../../faim-benchmarks/results/gpu/scifact-v19-ready/ret_scifact_20261122T124757Z_df5d93fc.md)
(`Query P50 = 104.52 ms`, `Query P95 = 159.15 ms`), beating `BM25-Baseline`
across every retrieval metric. Full scenario and multi-dataset results are
aggregated in [`RESULTS.md`](../../faim-benchmarks/results/RESULTS.md).

## Canonical documents

### Domain implementation guides

These six guides describe implemented cross-cutting subsystem behavior. They
are implementation references, not release claims:

- [Storage and ingestion](03-storage-and-ingestion/01-storage-lifecycle-and-hard-purge-guide.md)
- [Graph and FigView](04-graph-and-figview/01-figview-3d-physics-and-dag-lineage-guide.md)
- [Self-invention and evolution](05-self-invention-and-evolution/01-self-invention-cfp-and-topology-spec.md)
- [Autonomous learning, PPMI bridges, QRL, and worker isolation](05-self-invention-and-evolution/02-autonomous-learning-and-worker-isolation.md)
- [Physics and real-time SSE](06-physics-and-realtime-sse/01-fractal-physics-stream-and-sse-spec.md)
- [Control-plane UI and authentication](07-control-plane-ui-and-auth/01-control-plane-ui-layout-and-auth-guide.md)
- [Observability, timestamps, and logging](08-observability-timestamps-and-logging/03-timestamps-event-journal-and-logging-guide.md)

### Architecture

- [End-to-end architecture](01-architecture/01-end-to-end-architecture.md)
- [Query and temporal-memory contract](01-architecture/02-technical-memory-contract.md)
- [Zero-ML retrieval, relational concept graph, and Concept-Expanded MaxSim](01-architecture/03-zero-ml-retrieval-and-concept-expansion.md)
- [Current code map](09-implementation/01-current-code-map.md)
- [Retrieval and benchmark hardening record](14-research/03-retrieval-production-hardening-2026-11-18.md)

### Implementation quality and verification

- [Current code map](09-implementation/01-current-code-map.md)
- [Documentation audit](09-implementation/02-documentation-audit.md)
- [Coverage master plan](08-observability-timestamps-and-logging/01-coverage-master-plan.md)
- [Coverage status](08-observability-timestamps-and-logging/02-coverage-status.md)

### API and user guides

- [API documentation](02-api/01-api-documentation.md)
- [API keys](12-user-guides/01-api-keys.md)
- [Evolution](12-user-guides/02-evolution.md)
- [Providers](12-user-guides/03-providers.md)
- [Storage](12-user-guides/04-storage.md)

### Operations

- [Docker deployment](10-operations/01-deployment.md)
- [Operational runbook](10-operations/03-runbook.md)
- [Security baseline](10-operations/04-security-hardening.md)
- [SLO and on-call runbook](10-operations/05-slo-runbook.md)
- [GPU passthrough, CPU fallback, and HMAC auth caching](10-operations/06-gpu-passthrough-and-auth-caching.md)
- [GitHub branch-protection policy](10-operations/02-github-branch-protection.md)
- [CI, semantic releases, and deployment](10-operations/07-ci-and-releases.md)

### Security

- [Production hardening contract](11-security/02-production-hardening.md)
- [Data classification](11-security/01-data-classification.md)
- [Threat model](11-security/04-threat-model.md)
- [TLS deployment guidance](11-security/05-tls.md)
- [Frontend integration security guide](11-security/03-security-guide.md)

### Research and benchmark analysis

- [Retrieval improvement MoSCoW plan](14-research/01-retrieval-implementation-moscow-plan.md)
- [Retrieval and latency research report](14-research/02-retrieval-latency-research-report-2026-11-18.md)
- [Retrieval production-hardening record](14-research/03-retrieval-production-hardening-2026-11-18.md)
- [Research positioning and evaluation discipline](14-research/04-research-positioning.md)
- [Benchmark evidence and publication rules](13-benchmarks/01-benchmark-evidence.md)
- [Production benchmark suite and latency breakdown (2026-11-22)](13-benchmarks/02-production-benchmark-suite-2026-11-22.md)
- [Multi-scenario CPU/GPU/Granite benchmark results (2026-11-24)](13-benchmarks/03-multi-scenario-benchmark-results-2026-11-24.md)

## Archived material

Historical drafts, design mock-ups, and unmapped documents were removed from the
canonical documentation tree during documentation cleanup; prior revisions
remain inspectable in Git history.

## Updating this set

When a route, service, environment variable, or user-facing page changes,
update the affected canonical document in the same change. Do not describe a
planned feature as implemented, and do not report a test result without the
command, date, and inspectable artifact that produced it.
