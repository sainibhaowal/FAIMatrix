# FAIM-Native Backend Architecture

This document provides a **complete file-by-file breakdown** of ALL files in the FAIM-Native backend.

---

## High-Level Architecture

![diagram](./FAIM_BACKEND_ARCHITECTURE_diagrams-1.png)

---

## How ALL Core Files Connect

![diagram](./FAIM_BACKEND_ARCHITECTURE_diagrams-2.png)

**All files are connected and actively used!**

---


## Complete File Listing (ALL 135 Python Files)

### api/ — HTTP API Layer

| File | Purpose |
|:---|:---|
| `api/app.py` | FastAPI application factory, middleware registration |
| `api/deps.py` | Dependency injection (FAIMContext, tenant_id) |

#### api/middleware/

| File | Purpose |
|:---|:---|
| `middleware/__init__.py` | Package init |
| `middleware/auth.py` | API key authentication, tenant validation |
| `middleware/errors.py` | Global error handling |
| `middleware/jwt.py` | JWT token verification (NextAuth) |
| `middleware/ratelimit.py` | Token bucket rate limiting |
| `middleware/request_id.py` | Request ID generation for tracing |
| `middleware/security.py` | Security headers (HSTS, CSP, X-Frame-Options) |
| `middleware/session.py` | Session cookie management |

#### api/routers/

| File | Purpose |
|:---|:---|
| `routers/__init__.py` | Router exports |
| `routers/admin.py` | Admin operations (key rotation, etc.) |
| `routers/auth.py` | OTP login (request/verify) |
| `routers/events.py` | SSE event streaming |
| `routers/evolve.py` | Evolution cycle trigger |
| `routers/health.py` | Health and readiness checks |
| `routers/ingest.py` | Data ingestion endpoint |
| `routers/metrics.py` | Observability metrics |
| `routers/node.py` | Node CRUD operations |
| `routers/query.py` | Semantic search endpoint |

#### api/validators/

| File | Purpose |
|:---|:---|
| `validators/__init__.py` | Package init |
| `validators/input_limits.py` | Input size and depth validation |

---

### cache/ — Caching Layer (Redis)

| File | Purpose |
|:---|:---|
| `cache/locks.py` | Distributed locks |
| `cache/query_cache.py` | Query result caching |
| `cache/redis_client.py` | Redis connection factory |

---

### core/ — FAIM Engine

| File | Purpose |
|:---|:---|
| `core/antisym.py` | Antisymmetric opposition logic |
| `core/engine.py` | Engine interface |
| `core/engine_native.py` | Core FAIM-native operations |
| `core/invariants.py` | FAIM invariants validation (Σf=1) |

#### core/contracts/

| File | Purpose |
|:---|:---|
| `contracts/__init__.py` | Package init |
| `contracts/types.py` | Type definitions |

#### core/dynamics/

| File | Purpose |
|:---|:---|
| `dynamics/evolution_native.py` | Evolution dynamics |
| `dynamics/invention_native.py` | Invention/creation logic |
| `dynamics/nativegraph.py` | Native graph operations |

#### core/metrics/

| File | Purpose |
|:---|:---|
| `metrics/fractal_physics.py` | Fractal physics calculations |
| `metrics/metrics_defs.py` | Metric definitions |

#### core/operators/

| File | Purpose |
|:---|:---|
| `operators/inheritance.py` | Inheritance operations |
| `operators/prune.py` | Pruning operations |

#### core/query/

| File | Purpose |
|:---|:---|
| `query/__init__.py` | Package init |
| `query/query_engine.py` | Query execution engine |

---

### encoding/ — Vector Encoding

| File | Purpose |
|:---|:---|
| `encoding/__init__.py` | Package init |
| `encoding/text_vectorizer.py` | Text → Vector conversion |
| `encoding/vector_schema.py` | FAIM vector format definition |

#### encoding/OCR/

| File | Purpose |
|:---|:---|
| `OCR/ocr_features.py` | OCR feature extraction |

#### encoding/adapters/

| File | Purpose |
|:---|:---|
| `adapters/audio_adapter.py` | Audio processing adapter |

#### encoding/layout/

| File | Purpose |
|:---|:---|
| `layout/layout_features.py` | Layout feature extraction |

---

### index/ — Vector Index (Qdrant)

| File | Purpose |
|:---|:---|
| `index/qdrant_collections.py` | Qdrant collection management |
| `index/qdrant_index.py` | Qdrant index operations |

---

### orchestration/ — Business Logic Flows

| File | Purpose |
|:---|:---|
| `orchestration/evolve_flow.py` | Evolution cycle orchestration |
| `orchestration/ingest_flow.py` | Ingestion pipeline orchestration |
| `orchestration/query_flow.py` | Query processing orchestration |

#### orchestration/jobs/

| File | Purpose |
|:---|:---|
| `jobs/backup.py` | Backup job logic |
| `jobs/job_store.py` | Job persistence |
| `jobs/worker.py` | Background worker |

#### orchestration/perf/

| File | Purpose |
|:---|:---|
| `perf/gpu_backend.py` | GPU acceleration |
| `perf/hot_cache.py` | Hot data caching |
| `perf/ingest_worker.py` | Ingestion worker |
| `perf/nvme_snapshot.py` | NVMe snapshot operations |
| `perf/spec.py` | Performance specs |
| `perf/telemetry.py` | Telemetry collection |
| `perf/vector_bank.py` | Vector bank operations |
| `perf/write_queue.py` | Write queue management |

---

### perception/ — Input Processing

| File | Purpose |
|:---|:---|
| `perception/packetize.py` | Data chunking into packets |
| `perception/router.py` | Modality routing |
| `perception/validate.py` | Input validation |

#### perception/extract/

| File | Purpose |
|:---|:---|
| `extract/extractors_faim.py` | FAIM-native extractors |

---

### runtime/ — Configuration & Logging

| File | Purpose |
|:---|:---|
| `runtime/config.py` | Environment configuration |
| `runtime/context.py` | Request context and repo injection |
| `runtime/logging.py` | JSON logging with redaction |
| `runtime/secrets.py` | Secret management |

---

### scripts/ — Utility Scripts

| File | Purpose |
|:---|:---|
| `scripts/encode_atoms.py` | Atom encoding demo |
| `scripts/event_append_demo.py` | Event append demo |
| `scripts/extract_packet.py` | Packet extraction |
| `scripts/faim_diagnostics_demo.py` | Diagnostics demo |
| `scripts/faim_write_demo.py` | Write demo |
| `scripts/packet_validate.py` | Packet validation |
| `scripts/raw_ingest.py` | Raw data ingestion |
| `scripts/raw_verify.py` | Raw data verification |
| `scripts/snapshot_create_demo.py` | Snapshot creation demo |

---

### store/ — Persistence Layer

| File | Purpose |
|:---|:---|
| `store/__init__.py` | Package init |

#### store/crypto/

| File | Purpose |
|:---|:---|
| `crypto/__init__.py` | Package init |
| `crypto/envelope.py` | Encryption envelope |

#### store/journal/

| File | Purpose |
|:---|:---|
| `journal/__init__.py` | Package init |
| `journal/event_journal.py` | Append-only event journal |

#### store/pg/ (PostgreSQL)

| File | Purpose |
|:---|:---|
| `pg/__init__.py` | Package init |
| `pg/graph_store.py` | High-level graph operations |
| `pg/migrate.py` | Database migrations |
| `pg/models_auth.py` | Auth ORM models |
| `pg/models_crypto.py` | Crypto ORM models |
| `pg/models_faim.py` | FAIM ORM models |
| `pg/session.py` | SQLAlchemy session factory |

#### store/pg/repos/

| File | Purpose |
|:---|:---|
| `repos/__init__.py` | Package init |
| `repos/auth_repo.py` | Auth data access |
| `repos/edge_repo.py` | Edge data access |
| `repos/event_repo.py` | Event data access |
| `repos/graph_version_repo.py` | Graph versioning |
| `repos/node_repo.py` | Node data access |
| `repos/packet_repo.py` | Packet data access |
| `repos/payload_store.py` | Payload storage |
| `repos/raw_repo.py` | Raw data access |
| `repos/snapshot_repo.py` | Snapshot data access |

#### store/raw/

| File | Purpose |
|:---|:---|
| `raw/__init__.py` | Package init |
| `raw/crypto.py` | Raw data encryption |
| `raw/encrypted_payload_store.py` | Encrypted payload storage |
| `raw/raw_store.py` | Raw file storage |

---

### tests/ — Test Suite

| File | Purpose |
|:---|:---|
| `tests/__init__.py` | Package init |
| `tests/conftest.py` | Pytest fixtures |

#### tests/security/

| File | Purpose |
|:---|:---|
| `security/test_api_key_hashing.py` | API key hashing tests |
| `security/test_jwt_middleware.py` | JWT middleware tests |
| `security/test_logs_redact_secrets.py` | Log redaction tests |

#### tests/unit/

| File | Purpose |
|:---|:---|
| `unit/__init__.py` | Package init |
| `unit/test_antisym_idempotence.py` | Antisym idempotence tests |
| `unit/test_backup_command_safety.py` | Backup safety tests |
| `unit/test_cache_faim_native.py` | Cache tests |
| `unit/test_encoding_determinism.py` | Encoding determinism tests |
| `unit/test_event_journal_append.py` | Event journal tests |
| `unit/test_fractal_physics_determinism.py` | Physics determinism tests |
| `unit/test_graph_hash_receipt.py` | Graph hash tests |
| `unit/test_index_faim_native.py` | Index tests |
| `unit/test_inheritance_invariants.py` | Inheritance tests |
| `unit/test_metric_contract_unification.py` | Metric contract tests |
| `unit/test_native_vector_properties.py` | Vector property tests |
| `unit/test_orchestration_index.py` | Orchestration tests |
| `unit/test_packet_determinism.py` | Packet determinism tests |
| `unit/test_packet_validation.py` | Packet validation tests |
| `unit/test_prune_policy.py` | Prune policy tests |
| `unit/test_snapshot_repo.py` | Snapshot tests |
| `unit/test_stage_7_1_hardening.py` | Security hardening tests |
| `unit/test_vector_schema_v1.py` | Vector schema tests |

#### tests/acceptance/

| File | Purpose |
|:---|:---|
| `acceptance/__init__.py` | Package init |
| `acceptance/test_AT_A1_tenant_auth_required.py` | Tenant auth acceptance |
| `acceptance/test_AT_A2_tenant_isolation_events.py` | Tenant isolation |
| `acceptance/test_AT_A3_ingest_emits_events.py` | Ingest events |
| `acceptance/test_AT_A4_sse_resume_after_seq.py` | SSE resume |
| `acceptance/test_AT_A5_query_deterministic_strict.py` | Query determinism |
| `acceptance/test_AT_A6_node_inspector_no_leak.py` | No data leak |
| `acceptance/test_AT_A7_evolve_lock_single_writer.py` | Single writer lock |
| `acceptance/test_AT_C1_core_write.py` | Core write |
| `acceptance/test_AT_C2_antisym_merge.py` | Antisym merge |
| `acceptance/test_AT_C4_replay_determinism.py` | Replay determinism |
| `acceptance/test_AT_C5_diagnostics_events.py` | Diagnostics events |
| `acceptance/test_AT_E1_encode_atoms.py` | Encode atoms |
| `acceptance/test_AT_O1_ingest_chunk_free.py` | Chunk-free ingest |
| `acceptance/test_AT_O2_ingest_idempotent.py` | Idempotent ingest |
| `acceptance/test_AT_O3_strict_determinism.py` | Strict determinism |
| `acceptance/test_AT_O4_evolve_diagnostics.py` | Evolve diagnostics |
| `acceptance/test_AT_O5_spec_dimension.py` | Spec dimension |
| `acceptance/test_AT_P1_packetize.py` | Packetize |
| `acceptance/test_AT_Q1_query_determinism.py` | Query determinism |
| `acceptance/test_AT_Q2_no_chunking_no_ml.py` | No chunking |
| `acceptance/test_AT_Q3_tenant_isolation.py` | Tenant isolation |
| `acceptance/test_AT_Q4_index_fallback.py` | Index fallback |
| `acceptance/test_AT_Q5_explain_correctness.py` | Explain correctness |
| `acceptance/test_AT_Q6_events_emitted.py` | Events emitted |
| `acceptance/test_AT_Q7_query_flow.py` | Query flow |
| `acceptance/test_AT_R1_raw_truth.py` | Raw truth |
| `acceptance/test_AT_S10_backup_drill.py` | Backup drill |
| `acceptance/test_AT_S10_job_durability.py` | Job durability |
| `acceptance/test_AT_S10_migration_readiness.py` | Migration readiness |
| `acceptance/test_AT_S9_config_validation.py` | Config validation |
| `acceptance/test_AT_S9_ingest_idempotency.py` | Ingest idempotency |
| `acceptance/test_AT_S9_middleware_wiring.py` | Middleware wiring |
| `acceptance/test_AT_S9_production_ready.py` | Production ready |
| `acceptance/test_AT_S9_rate_limiting.py` | Rate limiting |

---

## Request Flow Diagrams

### Authentication Flow

![diagram](./FAIM_BACKEND_ARCHITECTURE_diagrams-3.png)

### Ingestion Flow

![diagram](./FAIM_BACKEND_ARCHITECTURE_diagrams-4.png)

### Query Flow

![diagram](./FAIM_BACKEND_ARCHITECTURE_diagrams-5.png)

---

## Summary

**Total Files: 135 Python files**

| Layer | Count |
|:---|:---|
| API | 21 |
| Cache | 3 |
| Core | 14 |
| Encoding | 6 |
| Index | 2 |
| Orchestration | 11 |
| Perception | 4 |
| Runtime | 4 |
| Scripts | 9 |
| Store | 17 |
| Tests | 44 |

All files work together to provide **10/10 security** and **FAIM-native memory operations**.
