# Changelog

All notable changes to **FAIM-Native** (`sainibhaowal/FAIMatrix`) are documented in this file.

This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html), and integrates with [`semantic-release`](.releaserc.json). Entries before tag `v0.5.0` summarize the foundational engineering milestones from repository initialization (`2025-12-27`) through `v0.5.0` (`2026-09-03`).

---

## [Unreleased]

### Added
- **Retrieval production foundation & zero-ML expansion (`PR #2`, Nov 2026):**
  - Collision-free stemmed + surface + adjacent-bigram `InvertedIndex` (`BM25+`) with memoized Porter stemming and single-flight `GraphIndexArtifacts` RAM caching keyed by `(tenant_id, graph_id, graph_version, include_dense)`.
  - Multi-hop typed **Relational Concept Graph** (`Synonym`, `Canonical`, `FormOf`, `DomainBridge`, `Causes`, `HasPrerequisite`, `PartOf`, `UsedFor`, `IsA`, `CapableOf`, `AtLocation`, `RelatedTo`) with bounded hub-dampened spreading.
  - **Concept-Expanded MaxSim** (`late_interaction_native.py`) capping 1-hop concept neighbor matches strictly below exact surface matches.
  - Background learning loops isolated into dedicated `worker-ingest` and `worker-evolve` pools: Corpus-Learned **PPMI & 2nd-Order Co-Occurrence Bridges** (`cooccurrence_bridge.py`) and asynchronous Redis **Query-to-Evidence Reinforcement Learning (QRL)** (`query_reinforcement.py`).
  - Expanded unit test coverage across MCP OAuth, events/providers routers, retrieval acceleration, concept MaxSim, QRL, and worker/GPU fallback paths.
- **Public black-box benchmark harness (`faim-benchmarks`, Nov 2026):**
  - Standalone HTTP-only evaluation harness (`faim-bench`) supporting BEIR (`SciFact`, `NFCorpus`, and opt-in `FiQA`, `TREC-COVID`, `ArguAna`) and memory/QA datasets (`LoCoMo`, opt-in `LongMemEval`), writing SHA-256-verified JSON and Markdown reports.
  - 6-scenario comparative runner, automated `RESULTS.md` aggregator, and bidirectional GPU/CPU fallback test coverage (`36a2aa8`).
- **GPU passthrough & hardware-aware autoscaling (Nov 2026):**
  - Integrated CUDA GPU passthrough (`TORCH_INDEX_URL`, `FAIM_CONTAINER_RUNTIME`, `NVIDIA_VISIBLE_DEVICES`, `FAIM_MIN_CUDA_FREE_MIB`) and automatic CUDA-to-CPU fallback across `embedding_providers.py`, `VectorBank`, and 256-dim native kernels directly into [`docker-compose.yml`](docker-compose.yml).
  - Added hardware-aware CPU/RAM/VRAM autoscaler for native and GPU hybrid runtimes (`96c9684`).
- **Verified external benchmark & multi-scenario results (`READY`, Nov 2026):**
  - Full `BeIR/SciFact` (5,183 docs / 300 queries): `Recall@5 = 0.7554`, `nDCG@10 = 0.6878`, `MRR = 0.6570`, `MAP = 0.6464` (beating `BM25-Baseline` across all metrics, Query p50 reduced to `104.52 ms` on GPU stack).
  - Full `BeIR/NFCorpus` (3,633 docs / 323 queries): `Recall@5 = 0.1267`, `nDCG@10 = 0.3258`, `MRR = 0.5259`, `MAP = 0.1327` (beating `BM25-Baseline` across all metrics, Query p50 `97.20 ms`).
  - Published multi-scenario CPU/GPU/Granite comparison reports (`42bfc05`, `7f042ca`, `00207de`).

### Performance
- Short-TTL HMAC-SHA256 verified-key LRU cache in `auth.py` with immediate invalidation on key rotation/revocation and `graph_version`-keyed query metadata caching in `query_flow.py`.
- Tuned PostgreSQL WAL/buffer settings, CUDA encode batch sizes (`100`, `128`, `256`), and VRAM-aware worker concurrency (`48e42b9`, `4b43766`, `ddbcc95`).
- Added work-stealing parallel session writes and parallel QA evaluation in memory benchmark suites (`546e2fd`).

### Fixed
- Embedded repository release tags during deploy builds so `/version` and application headers display accurate version metadata (`0081ba7`, `f073193`, `869b4fd`).
- Fixed `GraphVersionRepo` race condition using atomic `ON CONFLICT ON CONSTRAINT graph_version_pkey DO UPDATE` upserts (`1d18fda`, `0771d4a`).
- Raised `FAIM_DB_IDLE_IN_TRANSACTION_TIMEOUT_MS` to `300s`/`600s` for long batch embedding and index build transactions (`7b5dfce`).
- Added HTTP keep-alive retries, bounded client concurrency (`6`), and `DATASETS` filter in benchmark runners (`daecf3c`), plus CI benchmark scope/OOM/empty-document fixes (`37b7397`, `4b5ed8f`, `04bb861`).
- Disabled heavy datasets (`fiqa`, `trec-covid`, `longmemeval`) by default while keeping them opt-in (`ca5bbfb`).

### Changed & Documentation
- Organized benchmark artifacts into clean `cpu/`, `gpu/`, and multi-scenario result directories (`d45b855`, `91259dc`).
- Moved CI/CD runbook into [CI, semantic releases, and deployment](faim_native/Docs/10-operations/07-ci-and-releases.md) and research framing into [Research positioning](faim_native/Docs/14-research/04-research-positioning.md), removing stale root status docs (`PROJECT_STATUS.md`, `EXPERIMENTAL_STATUS.md`, `ROADMAP.md`, root `CI_CD.md`), unused scratch scripts (`debug_csv.py`, `scripts/generate_resume_pdf.js`), local filesystem paths, and private infrastructure references.
- Consolidated Docker Compose overlays and environment templates into a single [`docker-compose.yml`](docker-compose.yml) (using `--profile vps`, `--profile test`, and `FAIM_CONTAINER_RUNTIME` / `NVIDIA_VISIBLE_DEVICES`) and a single canonical [`.env.example`](.env.example) / `.env` configuration pair, keeping `deploy/Caddyfile.vps` and `deploy/nginx.conf`.
- Updated [GOVERNANCE.md](GOVERNANCE.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SUPPORT.md](SUPPORT.md), [CODEOWNERS](.github/CODEOWNERS), and [README.md](README.md) to production documentation standards.

---

## [0.6.1](https://github.com/sainibhaowal/FAIMatrix/compare/v0.6.0...v0.6.1) (2026-09-10)

### Fixed
- Hardened LLM provider auto-discovery and dashboard runtime error handling (`0554cbf`).

---

## [0.6.0](https://github.com/sainibhaowal/FAIMatrix/compare/v0.5.2...v0.6.0) (2026-09-08)

### Added
- Evidence-led systems comparison and deployment-neutral architecture diagrams across documentation and landing surfaces (`4e332ad`, `7594ee8`).

### Fixed
- Kept production FastAPI readiness and pipeline diagnostic endpoints responsive under load (`bbe360f`).
- Aligned public claims and cache/backup ownership documentation strictly with implemented behavior (`06ca55e`, `106c054`, `1e142eb`).

---

## [0.5.2](https://github.com/sainibhaowal/FAIMatrix/compare/v0.5.1...v0.5.2) (2026-09-08)

### Fixed
- Isolated reverse-proxy upstream names and pointed the VPS frontend proxy at its dedicated API service, backed by upstream proxy configuration tests (`11797fc`, `9233cf9`, `ed4a431`).

---

## [0.5.1](https://github.com/sainibhaowal/FAIMatrix/compare/v0.5.0...v0.5.1) (2026-09-08)

### Added
- Automated GitHub Actions CI, manual `semantic-release` (`vX.Y.Z`), and guarded remote deployment workflows (`f3c478c`).
- End-to-end architecture mapping documentation (`c5f5893`).

### Fixed
- Hardened production deployment descriptors and runtime memory handling (`235179b`).
- Enforced frozen `pnpm` lockfile installs in frontend CI and Docker builds, tracked frontend helper libraries, and isolated SQLite test database directories across CI workers (`fde5ba2`, `6170d4b`, `c7c850c`, `6031749`, `7837918`).

---

## [0.5.0] (2026-09-03)

Consolidated initial tagged release covering all foundational phases from repository creation (`2025-12-27`) through full native memory graph, storage, security, self-evolution, and frontend implementation (`2026-09-03`).

### Core Engine, Retrieval & Cortex (`Dec 2025 - Aug 2026`)
- Promoted `faim_native` to the canonical production architecture (`99df5fb`) with deterministic 256-dimensional `v_native` encoding, SHA-256 content addressing, and PostgreSQL canonical persistence (`5c7ef26`, `2728c69`, `e7c8fd5`).
- Added FAIM Semantic Signature v1 retrieval layer (`8fec7a9`), deterministic Semantic Edge Typing & Weighting (`c29d9d7`), multi-stage pure-Python retrieval improvements (`e0fdeb1`, `b345f07`), topic clustering / figure nodes (`2d95030`), global search, and synchronous invention tracking (`649de11`).
- Established `faim_native/core/cortex/cortexagi` (`88dfbaf`) with domain tools (`8c6b88a`), adaptive 1-128 hop micro-batch traversal (`5ed81a3`), and multi-stage ADI retrieval (`993bf0a`).

### Storage, Ingestion & Provenance (`Feb 2026 - Aug 2026`)
- Implemented Phases P0-P2 and A-H storage contract freeze, content-addressed raw store, provenance anchors, upload cancellation, retention purge, crypto key rotation backfill, and lifecycle observability (`00df0ab` through `49e93a0`).
- Added real-time 0-100% upload byte progress tracking, granular 1%-step graph ingestion progression (`3e593bd`, `6ab5b13`), Qdrant timeout resilience (`c175e36`), SQL rollback safety on upload/delete (`651c604`, `f790744`, `548ced8`), `coactivations.tenant_id` schema fix (`7304705`), large-PDF OOM protection (`6232ea9`), and graph-scoped storage footprint reporting (`d1385e2`, `1d20f6c`).

### Security, Authentication & Compliance (`Jan 2026 - Aug 2026`)
- Completed Stage 11 security hardening (`07d82c0`, `c45b9eb`, `f9f13c4`, `c900231`): Argon2id API-key hashing, secret log redaction, encryption at rest, rate limiting, and CVE/Bandit checks.
- Implemented Phases K1-K7 tenant-scoped API key contracts, management routes/UI, authz middleware enforcement, and agent memory runtime API (`9e9c237` through `ab17f93`, `3ba5938`).
- Added optional TOTP two-factor authentication (`6ac8797`), direct TOTP routing, expanded skew tolerance (`f529518`, `d8f6f15`), and unified safe JSON auth handling (`d127b99`, `60a7cc2`).

### Self-Evolution & Runtime Contracts (`Feb 2026 - Aug 2026`)
- Implemented Phases S1-S7 autonomous self-evolution guardrails, durable scheduler state, worker fallback scheduling, skip observability, and step A/B dashboard controls (`ae883ee` through `4edcb16`, `5fdc909`).
- Implemented Phases R1-R8 unified `STRICT` / `FAST` / `RELAXED` profile and persist runtime policy across ingest, query, evolve, and UI (`a7c5ddd` through `877b8bb`).
- Completed durable query-reinforcement learning, theory generation, and synthesis invention bridge (`7a0fca1`).

### Frontend Control Plane & 3D FIG View (`Dec 2025 - Aug 2026`)
- Reorganized Next.js frontend into feature-based architecture (`98c31cf`) with Domain Studio / Command Center analytics Dashboard (`0e7223f`, `516e57e`, `bee36a3`).
- Delivered 3D FIG View Phases 2-7 (`7ce495d` through `595abfe`): interactive 3D graph canvas, layout modes, zoom/fit controls, node inspection, relation explorer, client-side `D`/`H`/`lambda` scorecard metrics, and Neural Audit Journal.
- Added LLM provider auto-discovery, thread reasoning/thinking system (`c5b2ec9` through `2f74e4b`), real Engine Benchmarks UI (`34fb857`, `e7da4ef`), and interactive multi-chapter architecture manual overlay (`2be58ad` through `50d4911`).

### Infrastructure, Packaging & Project Policy (`Jan 2026 - Sep 2026`)
- Built Stage 10.1 production deployment pack (`9d359a1` through `e8d5102`), PostgreSQL backup/restore drill automation, SQL migration tracking (`7228748`), BuildKit cache mounts (`1ff553b`, `9cb7360`, `16bd493`), and consolidated local/VPS/test Docker Compose stacks (`9aadafd`, `02c0397`).
- Established Apache License 2.0, CC BY 4.0 documentation licensing, `TRADEMARKS.md`, `THIRD_PARTY_NOTICES.md`, `SECURITY.md`, `SUPPORT.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `GOVERNANCE.md`.
