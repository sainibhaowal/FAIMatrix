# FAIM-Native: Master Production Specification

> **Version:** 0.10.0 (Production Mature)  
> **Status:** MASTER SOURCE OF TRUTH  
> **Doctrine:** Native DNA | Absolute Determinism | 10/10 Security

---

## 1. Executive Summary

FAIM (Fractal Artificial Intelligence Matrix) is a **native cognitive architecture** designed for absolute data provenance, multi-dimensional semantic mapping, and structural evolution. Unlike traditional RAG (Retrieval-Augmented Generation) systems, FAIM treats memory as a biological metabolism — constantly merging, pruning, and inventing new concepts based on **fractal physics**.

### Core Invariants:
1. **RawTruth is Immutable**: Original source bytes are stored in SHA256-hashed blobs.
2. **Postgres is the Journal**: All metadata, relationships, and events are stored in PostgreSQL.
3. **No ML Magic**: All distance calculations and rankings use deterministic math (Cosine similarity + Fractal scoring).
4. **Σf = 1 (Inheritance Law)**: Every child node's influence is perfectly balanced across its parents.
5. **Absolute Provenance**: Every change to the graph is recorded in an append-only event journal.

---

## 2. The 12-Layer System Architecture

FAIM is structured into 12 distinct layers, ensuring total separation of concerns and high scalability.

| Layer | Component | Description | Key Files |
|:---|:---|:---|:---|
| **1** | **Runtime** | The foundation. Config, secrets, and JSON logging. | `runtime/config.py`, `runtime/logging.py` |
| **2** | **Repository** | Database migrations and SQL schema management. | `store/pg/migrate.py`, `store/pg/schema.sql` |
| **3** | **Shield** | Cryptographic envelopes and JWT/API-key auth. | `store/crypto/envelope.py`, `api/middleware/auth.py` |
| **4** | **Senses** | Raw ingestion and deterministic extraction. | `perception/router.py`, `store/raw/raw_store.py` |
| **5** | **Handwriting**| Vectorization (256-dim) and packetizing. | `encoding/text_vectorizer.py`, `perception/packetize.py` |
| **6** | **Constitution** | Core types and Σf=1 invariant logic. | `core/contracts/types.py`, `core/invariants.py` |
| **7** | **Engine Room** | Inheritance, Antisymmetry, and Macro invention. | `core/engine_native.py`, `core/antisym.py` |
| **8** | **Journal** | Append-only event history (Provenance). | `store/journal/event_journal.py`, `store/pg/repos/event_repo.py` |
| **9** | **Durable Will** | Background workers and transactional job queue. | `orchestration/jobs/worker.py`, `orchestration/jobs/job_store.py` |
| **10** | **Muscle Memory**| Redis caching and distributed locks. | `cache/redis_client.py`, `cache/locks.py` |
| **11** | **Metabolism** | Evolution dynamics (merging/pruning). | `core/dynamics/evolution_native.py`, `core/metrics/fractal_physics.py` |
| **12** | **Recall** | Semantic recall engine and Qdrant indexing. | `core/query/query_engine.py`, `index/qdrant_index.py` |

---

## 3. The Cognitive Engine (Workflows)

### 3.1 Data Ingestion (From Bytes to Vectors)
1. **Perception**: Raw bytes are extracted into `EvidenceBlocks`.
2. **Packetizing**: Blocks are serialized into a `MemoryPacket`. A SHA256 hash is generated as the **Idempotency Key**.
3. **Encoding**: Text is converted into a **256-dimensional vector** using a deterministic hashed n-gram approach (No ML models used for vectorization to ensure consistency).
4. **Writing**: The `engine_native` upserts the atom node and computes inheritance.

### 3.2 Inheritance (Building the Genealogy)
When a new node enters the graph:
- It selects $k=8$ parents based on cosine similarity.
- It calculates **inheritance fractions** ($f$) such that $\sum_{i=1}^{k} f_i = 1.0$.
- This ensures that energy/influence is conserved throughout the entire hierarchy.

### 3.3 Antisymmetry (Conflict & Merging)
The system constantly scans for **Opposing Nodes** ($A$ vs $B$).
- If $sim(A, B) > 0.95$, the nodes are merged.
- A "winner" is selected deterministically (by UUID comparison).
- The "loser" is deactivated, and an `OPPOSE` edge is created with the original conflict score.

---

## 4. Fractal Physics & Metrics

FAIM uses structural metrics to determine the "health" of a digital mind.

### $D$ — Fractal Dimension
Measures the **semantic density** of the graph.
- **Low D**: Sparse, disconnected thoughts.
- **High D**: Densely interconnected, nuanced concepts.

### $H$ — Entropy
Measures the **disorder** or "noise" level.
- **Goal**: Minimize $H$ through the **Evolution Cycle** (merging and pruning).

### $\lambda$ — Evolution Pressure
The "force" that drives the system to think.
$$ \lambda = 0.5 \hat{N} + 0.3 (1 - \hat{R}) + 0.2 \hat{H} $$
- $\hat{N}$: Novelty (mean residuals of new nodes).
- $\hat{R}$: Redundancy (overlap between existing nodes).
- **High $\lambda$**: Triggers the **Invention Cycle** to create new `macro` nodes.

---

## 5. Security & Isolation Doctrine

FAIM is built for **10/10 Enterprise Security**.

1. **Multi-Tenant Isolation**: 
   - Every table has a `tenant_id` column with a `NOT NULL` constraint.
   - Database triggers reject any operation where `tenant_id` is missing.
2. **Middleware Wall**:
   - `JWTAuthMiddleware`: Verifies NextAuth session tokens.
   - `TenantAuthMiddleware`: Validates API keys and locks the request to a specific `tenant_id`.
3. **Cryptographic Provenance**:
   - Every `EventRecord` has a checksum including the previous event's hash (Blockchain-lite).
   - Data at rest is wrapped in cryptographic envelopes.
4. **Redacted Logs**:
   - All logs pass through a `RedactingFilter` that scrubs API keys, emails, and secrets automatically.

---

## 6. Operation & Lifecycle

### The Dream Cycle (Evolution)
The system runs the `run_evolve()` flow periodically:
1. **Acquires Lock**: Prevents conflicting writes.
2. **Computes Metrics**: Calculates $D$, $H$, and $\lambda$.
3. **Merges Nodes**: Combines redundant information.
4. **Prunes Noise**: Removes weak relationships.
5. **Invents Macro-Concepts**: If $\lambda$ is high, it creates new parent nodes to summarize patterns.

---

## 7. API Summary

The system is controlled via **18 production endpoints**.

| Group | Endpoints | Purpose |
|:---|:---|:---|
| **Auth** | 2 | Secure OTP-based login. |
| **Ingest** | 2 | File and text upload (idempotent). |
| **Query** | 1 | Semantic search with re-ranking. |
| **Graph** | 3 | Node details, lineage, and events. |
| **Evolve**| 1 | Manual evolution trigger. |
| **Admin** | 4 | Reindexing and snapshot management. |
| **Health**| 3 | Liveness, readiness, and versioning. |

> See [FAIM_API_DOCUMENTATION.md](./FAIM_API_DOCUMENTATION.md) for full schema details.

---

*Verified by Antigravity — January 20, 2026*
