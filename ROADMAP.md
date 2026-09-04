# Roadmap and release gates

FAIM-Native is a large-scope project spanning a memory data plane, graph engine, retrieval layer, evolution workflows, API, worker, frontend, security controls, and operations. The roadmap is intentionally capability- and evidence-based rather than date-based. Priorities may change as experiments expose new constraints.

## Phase 0 — Current: document and stabilize the research prototype

- keep the end-to-end local stack reproducible;
- make architecture, data flow, safety boundaries, and known limitations explicit;
- keep backend, frontend, integration, smoke, and security checks runnable;
- remove false confidence from historical stage reports and benchmark claims; and
- preserve provenance, versioning, backups, and operational visibility as core concerns.

## Phase 1 — Reproducible research release

- pin and document supported dependency and container versions;
- provide reproducible datasets or safe synthetic fixtures with licenses;
- publish a benchmark harness with baselines, ablations, and failure reporting;
- define API, storage, event, and migration compatibility policies; and
- publish configuration, hardware, latency, quality, and cost assumptions.

## Phase 2 — Public alpha hardening

- strengthen migration, rollback, backup, restore, retention, and re-encryption workflows;
- complete tenant-isolation, authentication, rate-limit, audit, and secret-management review;
- define supported OCR, embedding, database, queue, and deployment combinations;
- improve frontend error states and operator workflows; and
- establish release notes, deprecation notices, and upgrade guidance.

## Phase 3 — External evaluation

- compare against appropriate lexical, vector, RAG, graph, and hybrid baselines;
- measure retrieval quality, provenance quality, explanation usefulness, latency, cost, and reliability;
- publish negative results, regressions, known failure modes, and workload boundaries; and
- invite independent review of the architecture and benchmark methodology.

## Stable-release gates

The project should not be described as stable until the maintainers can demonstrate:

- documented and versioned public contracts;
- repeatable migrations with tested rollback and backup/restore;
- a security review appropriate to the supported deployment model;
- reproducible benchmark and regression evidence;
- explicit performance and data-volume limits;
- supported-environment and compatibility documentation;
- maintained issue, security, support, and incident processes; and
- a release artifact that can be upgraded and operated without relying on undocumented repository state.

## How to contribute to the roadmap

Open a focused issue or pull request with the problem, proposed change, affected contracts, test evidence, operational implications, and any provenance or tenant-isolation impact. Research contributions should include the hypothesis, baseline, evaluation protocol, and negative or inconclusive results where relevant. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
