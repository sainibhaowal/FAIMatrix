# Research positioning

FAIM-Native is an exploratory research and engineering project. It investigates whether a memory system can make provenance, graph structure, controlled evolution, and replayable lifecycle state first-class parts of the memory substrate rather than treating memory as only a collection of retrieved passages or embedding vectors.

This document describes the project's hypothesis and evaluation plan. It does not establish academic novelty, prior art, patentability, benchmark superiority, or production readiness.

## Problem framing

Long-lived memory systems must do more than retrieve semantically similar text. They may also need to preserve the source of a fact, distinguish evidence from derived structure, represent relationships and opposition, update knowledge without silently losing history, explain why a result was returned, and support recovery when an evolution step is incorrect.

These requirements create trade-offs among recall, precision, provenance, latency, storage cost, operational complexity, and explainability. FAIM-Native is intended as a concrete system in which those trade-offs can be measured rather than discussed only at the abstraction level.

## Architectural hypothesis

The working hypothesis is that a layered memory lifecycle can improve inspectability and controlled change:

1. raw inputs are retained as addressable evidence;
2. perception produces ordered evidence blocks with anchors and provenance;
3. canonical semantics and native representations become versioned memory objects;
4. graph operators represent inheritance, relations, opposition, and coactivation;
5. retrieval combines similarity with graph and lifecycle signals; and
6. evolution is guarded, observable, reversible, and recorded as events and versions.

The repository implements one testable version of this hypothesis. It does not imply that every workload benefits from this design or that graph-native memory should replace simpler vector, lexical, relational, or hybrid systems.

## Areas of investigation

- provenance-preserving memory objects and evidence anchors;
- deterministic native representations and replayable transformations;
- graph-aware retrieval, explanations, and contradiction/opposition signals;
- evented graph evolution, invention, maintenance, backup, and restore;
- tenant-aware operation across API, worker, storage, and frontend surfaces; and
- practical trade-offs between explainability, quality, latency, and cost.

## Responsible comparison

Comparisons with vector databases, RAG pipelines, knowledge graphs, symbolic systems, hybrid retrieval, and agent-memory frameworks should use published baselines and a fixed protocol. A useful report should identify:

- dataset composition, licensing, preprocessing, and leakage controls;
- baseline implementations, model/provider versions, and configuration;
- retrieval, provenance, explanation, latency, cost, and reliability metrics;
- ablations showing which architectural component changes the outcome;
- hardware, concurrency, storage, and operational assumptions; and
- failures, regressions, uncertainty, and cases where a simpler system is preferable.

## Claims the project is not making

FAIM-Native is not currently claiming:

- universal superiority over existing memory or retrieval architectures;
- that its design is definitively novel in the academic or legal sense;
- that deterministic native encoding is the best representation for every domain;
- that current benchmark or test results generalize to every dataset or deployment; or
- that the current repository is suitable for personal, production, regulated, or safety-critical use.

## Research questions

The project can support experiments such as:

- Does explicit evidence provenance improve human trust and debugging speed?
- When does graph context improve answer quality beyond passage retrieval?
- Can guarded evolution improve continuity without increasing harmful drift?
- Does deterministic replay make failures easier to diagnose and recover from?
- What are the latency, storage, and maintenance costs of the additional structure?
- Which workloads favor this architecture, and which favor a simpler baseline?

Results should be treated as evidence for or against specific hypotheses, not as proof of a universal architecture.

## Suggested reading order

Start with [`README.md`](README.md), then review [`docs/architecture_overview.md`](docs/architecture_overview.md), [`docs/Benchmarks_Publication/BENCHMARK_SPEC.md`](docs/Benchmarks_Publication/BENCHMARK_SPEC.md), [`EXPERIMENTAL_STATUS.md`](EXPERIMENTAL_STATUS.md), and [`PROJECT_STATUS.md`](PROJECT_STATUS.md). Contributors should also read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`GOVERNANCE.md`](GOVERNANCE.md).
