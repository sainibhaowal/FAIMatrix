# FAIM-Native Documentation

Production-grade, deterministic Store, Perception, Encoding, Core, Fractal Physics, Orchestration, Index/Cache, and API layers following FAIM-native doctrine.

## Quick Start

```bash
cd /home/sephi-asi/FAIM/faim/Faim_Native
./scripts/verify.sh  # Run all 416 tests
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FAIM-Native Stack                        │
├─────────────────────────────────────────────────────────────┤
│  Stage-11: Security Hardening (NEW)                          │
│  ├── API Key Hashing (Argon2id)                              │
│  ├── Log Redaction (RedactingFilter)                         │
│  ├── CVE Scanning (pip-audit, bandit)                        │
│  ├── Encryption at Rest (AES-256-GCM)                        │
│  └── Session Tokens, TLS, Container Hardening                │
├─────────────────────────────────────────────────────────────┤
│  Stage-10.1: Production Deployment Pack                      │
│  ├── Docker Compose (no secrets in YAML)                     │
│  ├── Entrypoint gating (refuses stale schema)                │
│  ├── Optional accel services (profiles)                      │
│  └── CI release gate script                                  │
├─────────────────────────────────────────────────────────────┤
│  Stage-10: Operational Hardening                              │
│  ├── Robust migrations (checksum-protected)                  │
│  ├── Durable background jobs (transactional queue)          │
│  ├── Backup/restore drill script                             │
│  └── Security & deployment documentation                     │
├─────────────────────────────────────────────────────────────┤
│  Stage-9: Production Ready                                   │
│  ├── Idempotency (dedup check + record)                      │
│  ├── Rate limiting (per-tenant token bucket)                │
│  ├── JSON Logging with correlation IDs                      │
│  ├── Payload bounds enforcement (4KB)                       │
│  └── /ready probe (K8s DB + Table health)                   │
├─────────────────────────────────────────────────────────────┤
│  Stage-8: Query Engine                                       │
│  ├── QueryPlan & Reranking                                   │
│  ├── Multi-tenant query isolation                            │
│  └── SSE status integration                                  │
├─────────────────────────────────────────────────────────────┤
│  Stage-7.1: Production Hardening                             │
│  ├── tenant_id NOT NULL on all tables                        │
│  ├── DB trigger rejects empty tenant                         │
│  ├── Constant-time API key comparison                        │
│  └── SSE with short-lived sessions                           │
├─────────────────────────────────────────────────────────────┤
│  Stage-7: API + SSE                                          │
│  ├── FastAPI with tenant auth                                │
│  ├── SSE event stream (Postgres-backed)                      │
│  └── Ingest/Query/Node/Evolve endpoints                      │
├─────────────────────────────────────────────────────────────┤
│  Stage-6: Index/Cache                                        │
│  ├── FAIMIndex (Qdrant + fallback) dim=256                  │
│  ├── QueryCache (version-aware keys)                        │
│  └── LockManager (Redis + file fallback)                    │
├─────────────────────────────────────────────────────────────┤
│  Stage-5: Orchestration                                      │
│  ├── run_ingest(), run_evolve()                             │
│  ├── No chunking, no ST, deterministic                      │
│  └── UI-ready event stream                                   │
├─────────────────────────────────────────────────────────────┤
│  Stage-4.1.1: Metric Contract                                │
│  └── MetricsSnapshot (UI/API schema)                         │
├─────────────────────────────────────────────────────────────┤
│  Stage-4.1: Fractal Physics                                  │
│  ├── PHI = 1.618, s = 1/PHI                                 │
│  ├── D (dimension), H (entropy), λ (pressure)               │
│  └── DIAGNOSTICS_SNAPSHOT events                             │
├─────────────────────────────────────────────────────────────┤
│  Stage-4: Core Physics                                       │
│  ├── FIG Graph (nodes + edges)                              │
│  ├── Inheritance (Σf=1) + Antisym (merge)                   │
│  └── Evolution + Invention                                   │
├─────────────────────────────────────────────────────────────┤
│  Stage-3: Encoding Layer                                     │
│  ├── FAIMVector v1 Schema (256 dims)                        │
│  └── Hashed N-Gram Vectorizer (no ML)                       │
├─────────────────────────────────────────────────────────────┤
│  Stage-2: Perception Layer                                   │
│  ├── EvidenceBlocks with Anchors                            │
│  └── MemoryPackets with Hashes                              │
├─────────────────────────────────────────────────────────────┤
│  Stage-1: Store Layer                                        │
│  ├── SHA256 Blob Storage                                     │
│  └── PostgreSQL Metadata                                     │
└─────────────────────────────────────────────────────────────┘
```

## Test Summary

```
======================= 416 passed, 1 skipped, 10 warnings in 3.10s ========================
```

| Stage     | Category              | Tests   |
| --------- | --------------------- | ------- |
| 1         | Store Layer           | 32      |
| 2         | Perception Layer      | 41      |
| 3         | Encoding Layer        | 49      |
| 4         | Core Physics          | 50      |
| 4.1       | Fractal Physics       | 29      |
| 4.1.1     | Metric Contract       | 15      |
| 5         | Orchestration         | 34      |
| 6         | Index/Cache           | 23      |
| 7         | API + SSE             | 40      |
| 7.1       | Production Hardening  | 19      |
| 8         | Query Engine          | 40      |
| 9         | Production Ready      | 38      |
| 10        | Operational Hardening | 6       |
| 10.1      | Production Deployment | 1       |
| 11        | Security Hardening    | 28      |
| **Total** |                       | **445** |

## Core Doctrine

| Principle                  | Implementation               |
| -------------------------- | ---------------------------- |
| **RawTruth is immutable**  | SHA256 blob storage          |
| **Postgres is truth**      | All metadata in PostgreSQL   |
| **No token chunking**      | EvidenceBlocks with anchors  |
| **Anchors mandatory**      | Every block has BlockAnchor  |
| **Deterministic ordering** | Blocks sorted by anchor      |
| **Deterministic hashes**   | SHA256 of canonical JSON     |
| **No ML models**           | Hashed n-grams + cosine      |
| **Fixed dimension**        | Always 256                   |
| **Σfractions = 1**         | Inheritance invariant        |
| **Events emitted**         | Every mutation logged        |
| **Fractal scaling**        | s = 1/PHI ≈ 0.618            |
| **D/H/λ diagnostics**      | Dimension, entropy, pressure |

## Fractal Physics (Stage-4.1)

### Constants

```python
PHI = (1 + √5) / 2  ≈ 1.618  # Golden ratio
GOLDEN_S = 1 / PHI  ≈ 0.618  # Scaling factor
```

### Metrics

- **D**: Fractal dimension (correlation dimension)
- **H**: Entropy (normalized Shannon)
- **λ**: Evolution pressure = 0.5N + 0.3(1-R) + 0.2H
- **R**: Redundancy (high-sim pairs)
- **N**: Novelty (mean residuals)
- **E**: Energy (bounded norms)

### Events

- `DIAGNOSTICS_SNAPSHOT` - D/H/λ/R/N/E at evolution start
- `EVOLUTION_COMPLETE` - With diagnostics_hash
- `INVENT_MACRO_NODE` - With λ_hat, redundancy_reduction

## Documentation Index

- [Store Layer Guide](./store_layer_guide.md) - SHA256 blobs + PostgreSQL
- [Perception Layer Guide](./perception_layer_guide.md) - Blocks + Packets
- [Encoding Layer Guide](./encoding_layer_guide.md) - FAIMVector + Hashed n-grams
- [Core Layer Guide](./core_layer_guide.md) - FIG Graph + Operators
- [Stage-4.1 Report](./stage_4_1_report.md) - Fractal Physics (D/H/λ)
- [Stage-4.1.1 Report](./stage_4_1_1_report.md) - Metric Contract Unification
- [Stage-7.1 Report](./stage_7_1_report.md) - Hardening & Triggers
- [Stage-8 Report](./stage_8_report.md) - Query Engine (rerank_faim)
- [Stage-9 Report](./stage_9_report.md) - Production Readiness (Fully Wired)
- [Stage-10 Report](./stage_10_report.md) - Operational Hardening
- [Stage-10.1 Report](./stage_10_1_report.md) - Production Deployment Pack
- [Stage-11 Report](./stage_11_report.md) - Security Hardening
- [Deployment Guide](./DEPLOYMENT.md) - Docker Compose deployment
- [TLS Guide](./DEPLOYMENT_TLS.md) - TLS configuration
- [Threat Model](./THREAT_MODEL.md) - Security threats & invariants
- [Data Classification](./DATA_CLASSIFICATION.md) - Sensitivity levels
- [Security Guide](./SECURITY_GUIDE.md) - Frontend integration security
- [Test Report](./test_report.md) - All 445 tests documented
- [API Reference](./api_reference.md) - Type definitions
- [Files Delivered](./files_delivered.md) - Complete file inventory

## Demo Scripts

```bash
# Full pipeline: file → extract → encode → write
python scripts/faim_write_demo.py sample.txt

# Display D/H/λ metrics
python scripts/faim_diagnostics_demo.py
```
