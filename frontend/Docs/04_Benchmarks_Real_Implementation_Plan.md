# 04_Benchmarks_Real_Implementation_Plan.md

**Date:** 2026-04-09  
**Status:** ✅ **FULLY IMPLEMENTED** — All 8 phases complete and live. Commit: `6ff4d02`  
**Scope:** STATE-OF-THE-ART benchmarking system for FAIM-Native with REAL measured performance data, stress testing, container telemetry, anomaly detection, and exportable reports.
**Architecture:** PostgreSQL:8020, Redis:8030, Qdrant:8040/8050, API:8000 (2 CPU / 1G RAM), Worker, Frontend:8010. All on Docker bridge network `faim-net`.

---

## CRITICAL: COMPETITIVE ANALYSIS — Why Current Plan Is Not Enough

### The Problem

As of April 2026, here are the published benchmark scores for AI memory systems:

| System | LOCOMO Score | LongMemEval | DMR | Latency (p95) | Requires Cloud LLM |
|--------|-------------|-------------|-----|----------------|:-------------------:|
| Supermemory | ~70% | **85.4%** | — | sub-300ms | Yes |
| Zep (Graphiti) | ~85% | — | **94.8%** | ~300ms | Yes |
| Letta/MemGPT | ~83.2% | — | 93.4% | — | Yes |
| Mem0 | 66.9% (self) / 58% (independent) | — | — | 1.44s | Yes |
| Mem0-graph | 68.4% | — | — | 2.59s | Yes |
| **FAIM-Native** | **Not tested** | **Not tested** | **Not tested** | **Not published** | **No** |

**FAIM has zero published scores on any industry-standard benchmark.** Without numbers, no claim is provable.

### What the Industry Benchmarks Actually Test

**LOCOMO (LOng-COntext MOnitor):**
- 600-turn conversations spanning 6-12 months across 32 sessions (~16K tokens)
- Tests: single-hop QA, multi-hop cross-session QA, temporal reasoning, event summarization
- Scored by LLM-as-Judge methodology

**LongMemEval (ICLR 2025):**
- 500 curated questions across 115K-1.5M token histories
- 5 abilities: information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention
- Industry's most rigorous memory benchmark

**DMR (MemGPT's benchmark):**
- Designed for agent memory evaluation with explicit conversation context

### Where FAIM Loses vs Competitors (Honest Assessment)

1. **No LOCOMO score** — Cannot claim accuracy without testing
2. **No LongMemEval score** — Cannot claim multi-session reasoning without testing
3. **No published latency comparison** — No head-to-head numbers
4. **No temporal reasoning claims** — Zep and Supermemory explicitly handle temporal queries
5. **No token efficiency numbers** — Mem0 claims 90% token savings, FAIM has no published comparison

### Where FAIM Wins — Capabilities NO Competitor Has

| Capability | FAIM | Mem0 | Supermemory | Zep | Letta |
|-----------|:----:|:----:|:-----------:|:---:|:-----:|
| **Deterministic** (NO ML, NO randomness in core) | YES | No | No | No | No |
| **Cryptographic integrity** (SHA256 on every vector + graph state) | YES | No | No | No | No |
| **Mathematical invariants** (8 verifiable guarantees) | YES | No | No | No | No |
| **Fractal physics** (D, H, Lambda, R, N, E) | YES | No | No | No | No |
| **Self-evolution** (automatic graph optimization without LLM) | YES | No | No | No | No |
| **No cloud LLM dependency** | YES | No | No | No | No |
| **Inheritance graph** (fraction sum = 1.0 invariant) | YES | No | No | No | No |
| **Antisymmetric merge** (deterministic deduplication) | YES | No | No | No | No |
| **Energy boundedness** (E ≤ 2.0 stability guarantee) | YES | No | No | No | No |
| **Multi-tenant crypto isolation** | YES | Partial | No | No | No |

**No existing benchmark tests ANY of these capabilities.** The industry benchmarks (LOCOMO, LongMemEval) test LLM-dependent conversational recall — they don't test determinism, integrity, or mathematical guarantees.

### The Strategy: Two-Pronged Benchmark Approach

**Prong 1: FAIM-Native Benchmark Suite (NEW)**
Define and publish benchmark categories that ONLY FAIM can pass. These prove capabilities no competitor has.

**Prong 2: Industry Benchmark Adapter (FUTURE)**
Build adapters to run LOCOMO and LongMemEval against FAIM, generating comparable scores. This is a separate project but the benchmarks page should show the framework.

---

## 0. Deep Understanding — What FAIM Actually Does

FAIM-Native is a **Fractal Antisymmetric Inheritance Memory graph engine**. Before designing benchmarks, here is what each operation actually computes and why its performance matters:

### 0.1 Core Pipeline (What To Benchmark)

**Ingest Flow** (`orchestration/ingest_flow.py`):
1. `perception.router.route_extraction` → EvidenceBlocks from raw files (PDF, DOCX, etc.)
2. `perception.packetize.create_packet` → MemoryPacket with SHA256 hash
3. `encoding.encode_packet` → FAIMVectors (256-dim, deterministic, NO ML)
4. `core.engine_native.write_atoms` → For each vector:
   - Upsert atom node to PostgreSQL (`node_repo.upsert_atom_node`)
   - Compute inheritance plan: find top-k parents by cosine similarity, compute fractions (must sum to exactly 1.0), compute residual (novelty proxy = `1 - cosine(child, weighted_parent_mix)`)
   - Antisym scan: find merge candidates with `opposition_score >= 0.95`, deterministically select winner by lower `vector_hash`, create opposition edge
   - Emit events: NODE_UPSERT, INHERITANCE_SET, MERGE, GRAPH_VERSION_BUMP
5. Bump graph version
6. IngestResult includes `phase_latency_ms` breakdown already

**Evolution Flow** (`orchestration/evolve_flow.py` → `core/dynamics/evolution_native.py`):
1. Compute full fractal diagnostics via `core/metrics/fractal_physics.py`:
   - **D_hat** (fractal dimension): Correlation-dimension estimate from pairwise cosine distances across 8 epsilon thresholds, linear regression on log(C(eps)) vs log(eps). O(n^2) pairwise.
   - **H_hat** (entropy): Shannon entropy of similarity histogram (20 bins over [-1,1]), normalized to [0,1]. Measures diversity.
   - **Redundancy R**: Fraction of pairs with cosine similarity > 0.9
   - **Novelty N**: Mean of all node residuals (where residual = 1 - inheritance fit)
   - **Lambda_hat** (evolution pressure): `0.50*N + 0.30*(1-R) + 0.20*H`. Higher = more pressure to evolve.
   - **Energy E**: Mean L2 norm of vectors scaled by golden ratio reciprocal (s = 1/PHI ≈ 0.618). Must stay bounded (E <= 2.0).
2. Adaptive merge threshold based on diagnostics
3. Merge/cancel high-redundancy pairs
4. Prune safe nodes (via `core/operators/prune.py`)
5. Self-invention: create macro nodes from coactivation patterns
6. Emit DIAGNOSTICS_SNAPSHOT event

**Query Flow** (`orchestration/query_flow.py` → `core/query/query_engine.py`):
1. Candidate recall: brute-force from Postgres OR index-based (Qdrant)
2. FAIM re-ranker scoring formula:
   ```
   score = 0.40*cosine(q, n) + 0.15*clamp(residual) - 0.10*opposition_penalty
         - 0.10*redundancy_penalty + 0.10*recency_boost + 0.10*log1p(touch_count)/10
         - 0.05*level_penalty
   ```
3. Top-k results with full explain payload (parents, fractions, oppositions, evidence anchor)

### 0.2 Infrastructure Already Present (Must Reuse, Not Duplicate)

| Component | File | What it already provides |
|-----------|------|------------------------|
| **ThroughputTracker** | `orchestration/perf/telemetry.py` | Rolling 30s window, `record(count)` + `get_throughput()` → synapses/sec. Has a `global_throughput` singleton. |
| **SpeedBudget profiles** | `orchestration/perf/spec.py` | 7 named profiles (STRICT, FAST, RELAXED, CORE_DEV, CORE_REALTIME, CORE_SCALE, CORE_HARDENED) with concrete p95 latency targets, insert QPS targets, max nodes, RAM limits |
| **HotNodeCache + CacheStats** | `orchestration/perf/hot_cache.py` | LRU cache with hits/misses/loads/puts/evictions counters. Has `hit_rate()` method. |
| **MetricsScorecard API** | `api/routers/metrics.py` → `GET /api/v1/metrics/scorecard?graph_id=X` | Returns D_hat, H_hat, lambda_hat, redundancy, novelty, energy, node_count, edge_count from latest DIAGNOSTICS_SNAPSHOT event |
| **IngestResult.phase_latency_ms** | `orchestration/ingest_flow.py` | Already captures per-phase latency breakdown (extract, packetize, encode, write, diagnostics) |
| **EvolveResult.latency_ms** | `orchestration/evolve_flow.py` | Total evolve latency |
| **Health/Ready endpoints** | `api/routers/health.py` | `/health` (liveness), `/ready` (DB + tables + migration check) |
| **Event system** | `store/pg/repos/event_repo.py` | Append-only event journal with DIAGNOSTICS_SNAPSHOT, NODE_UPSERT, MERGE, INHERITANCE_SET, GRAPH_VERSION_BUMP |
| **BenchmarkPoint type** | `frontend/src/types/api.ts` | Already defined: `{ timestamp, nodes, cr, redundancy, drift, latency: { store_p50_ms, retrieve_p50_ms, retrieve_p95_ms } }` |
| **API client** | `frontend/src/lib/api-client.ts` | `apiGet<T>(path)`, `apiPost<T>(path, body)` with tenant headers |

### 0.3 Current Benchmarks Page Problem (What Is Fake)

File: `frontend/src/app/(app)/dashboard/benchmarks/page.tsx`

Everything on this page is hardcoded:
- `94.2` maturity score → **no API call, no computation**
- `242ms` latency → **static string, not measured**
- `1.2k` throughput → **static string, not measured**
- `99.98%` stability → **static string, not measured**
- Model performance matrix with `gemini-1.5-pro`, `claude-3-sonnet`, `gpt-4o-mini`, `gpt-4-turbo` → **fake data, FAIM does NOT use these LLMs for its core engine** (FAIM is NO ML, NO RANDOMNESS)
- Diagnostic panel: `14% novelty increase`, `99.2% recall`, `98.7% precision`, `0.24 density` → **all fabricated**

**Critical insight:** FAIM does NOT use ML models for its core operations. The "model performance matrix" showing LLM names is misleading. Real benchmarks must measure FAIM's actual operations: ingest, evolve, query, vector encoding, inheritance computation, antisym merge, fractal diagnostics.

---

## 1. What Real FAIM Benchmarks Must Measure

Based on deep code reading, here are the ACTUAL operations that matter:

### 1.1 Ingest Pipeline Benchmarks

| Metric | Source | How to measure | Why it matters |
|--------|--------|----------------|----------------|
| **Ingest Latency (total)** | `IngestResult.latency_ms` | Already returned by `/api/v1/ingest` response | Core user-facing metric |
| **Phase Breakdown** | `IngestResult.phase_latency_ms` | Already returned: extract, packetize, encode, write, diagnostics | Identify bottleneck phase |
| **Nodes Written/sec** | `IngestResult.nodes_written` / latency | Compute from existing response data | Throughput capacity |
| **Dedup Hit Rate** | `IngestResult.dedup_hit` counts | Count dedup_hit=true vs total ingests | Storage efficiency |
| **Merges per Ingest** | `IngestResult.merges` | Already returned | Redundancy detection effectiveness |
| **Vectors Encoded/sec** | `IngestResult.vector_count` / encode phase time | Compute from phase_latency_ms["encode"] | Encoding throughput |

### 1.2 Evolution Benchmarks

| Metric | Source | How to measure |
|--------|--------|----------------|
| **Evolve Latency** | `EvolveResult.latency_ms` | Already returned by `/api/v1/evolve` response |
| **Merges per Cycle** | `EvolveResult.merges` | Already returned |
| **Prunes per Cycle** | `EvolveResult.prunes` | Already returned |
| **Inventions per Cycle** | `EvolveResult.inventions` | Already returned |
| **Diagnostics Compute Time** | Part of evolve latency | Extract from phase breakdown |

### 1.3 Fractal Physics Benchmarks (FAIM-Specific)

| Metric | Source | Valid Range | What it means |
|--------|--------|-------------|---------------|
| **D_hat** (Fractal Dimension) | `GET /api/v1/metrics/scorecard` | [0, 10] | Structural complexity. Higher = more complex graph topology |
| **H_hat** (Entropy) | scorecard | [0, 1] | Diversity. 1 = max disorder, 0 = uniform |
| **Lambda_hat** (Evolution Pressure) | scorecard | [0, 1] | 0.50*N + 0.30*(1-R) + 0.20*H. Higher = graph needs more evolution |
| **Redundancy R** | scorecard | [0, 1] | Fraction of pairs with sim > 0.9. Lower is better |
| **Novelty N** | scorecard | [0, 1] | Mean residual. Higher = more new information |
| **Energy E** | scorecard | [0, 2] | Must stay bounded. E > 2 = invariant violation |
| **Compression Ratio** | scorecard | CR = nodes/edges | Storage efficiency |

### 1.4 Query Benchmarks

| Metric | Source | How to measure |
|--------|--------|----------------|
| **Query Latency** | `/api/v1/query` response time | Measure round-trip time |
| **Candidate Recall Count** | QueryPlan.candidate_ids length | From query explain |
| **Re-rank Time** | Time between recall and final result | Profile rerank_faim() |
| **Cache Hit Rate** | `HotNodeCache.stats.hit_rate()` | Already computed in hot_cache.py |

### 1.5 System Health Benchmarks

| Metric | Source | How to measure |
|--------|--------|----------------|
| **Graph Node Count** | `node_repo.count(graph_id)` | Already in scorecard |
| **Graph Edge Count** | `edge_repo.count(graph_id)` | Already in scorecard |
| **Graph Version** | `gv_repo.get(graph_id)` | Already in scorecard |
| **DB Connection Status** | `/ready` endpoint | Already implemented |
| **Cache Stats** | `HotNodeCache.stats` | hits, misses, evictions, hit_rate |
| **Throughput (synapses/sec)** | `global_throughput.get_throughput()` | Already computed in telemetry.py |
| **Active SpeedBudget Profile** | `get_speed_budget()` | From env config |
| **Invariant Status** | `check_all_invariants()` | Run on demand from core/invariants.py |

---

## 2. Where to Implement — Exact File Map

### 2.1 New Backend Files

| # | File | Purpose |
|---|------|---------|
| 1 | `faim_native/api/routers/benchmarks.py` | New router: 3 endpoints for benchmark data |
| 2 | `faim_native/api/services/benchmark_collector.py` | Aggregation service that pulls from existing sources (scorecard, telemetry, cache stats, event journal) |
| 3 | `faim_native/store/pg/migrations/0011_benchmark_samples.sql` | New table for time-series metric storage |
| 4 | `faim_native/store/pg/repos/benchmark_repo.py` | Insert/query benchmark samples |
| 5 | `faim_native/api/middleware/latency_collector.py` | Lightweight middleware to record per-request latency to benchmark_samples table |
| 6 | `tests/acceptance/test_AT_benchmarks_api_surface.py` | API surface tests |
| 7 | `tests/unit/test_benchmark_collector.py` | Unit tests for aggregation logic |

### 2.2 New Frontend Files

| # | File | Purpose |
|---|------|---------|
| 1 | `frontend/src/types/benchmarks.ts` | TypeScript contracts matching backend response shapes |
| 2 | `frontend/src/lib/benchmarkApi.ts` | API client functions for benchmark endpoints |
| 3 | `frontend/src/components/benchmarks/BenchmarkMetricCard.tsx` | Reusable metric card (replaces hardcoded stat items) |
| 4 | `frontend/src/components/benchmarks/FractalPhysicsPanel.tsx` | Panel showing D, H, Lambda, R, N, E with real gauge visualizations |
| 5 | `frontend/src/components/benchmarks/PipelineLatencyChart.tsx` | Recharts bar chart: ingest phase breakdown (extract, packetize, encode, write) |
| 6 | `frontend/src/components/benchmarks/InvariantStatusPanel.tsx` | Shows invariant check results (inheritance sum, boundedness, orphan edges, fractal bounds) |

### 2.3 Modified Files (Must Update)

| # | File | Change | Risk |
|---|------|--------|------|
| 1 | `faim_native/api/app.py` | Add `benchmarks_router` to `create_app()` router registration (line ~155-188) | Low: additive only, same pattern as existing routers |
| 2 | `faim_native/api/routers/__init__.py` | Add `benchmarks_router` import | Low: additive only |
| 3 | `frontend/src/app/(app)/dashboard/benchmarks/page.tsx` | Complete rewrite: replace hardcoded data with API calls to real data | Medium: isolated page, no other page depends on it |
| 4 | `frontend/src/types/api.ts` | Extend `BenchmarkPoint` type if needed (already partially defined) | Low: additive |

### 2.4 Files to NOT Touch

- `faim_native/core/engine_native.py` — Engine logic must not change
- `faim_native/core/antisym.py` — Antisym operator must not change
- `faim_native/core/invariants.py` — Invariant checks are read-only consumers
- `faim_native/core/metrics/fractal_physics.py` — Already emits all we need via DIAGNOSTICS_SNAPSHOT
- `faim_native/core/query/query_engine.py` — Query logic must not change
- `faim_native/orchestration/ingest_flow.py` — Already returns phase_latency_ms
- `faim_native/orchestration/evolve_flow.py` — Already returns latency_ms
- `faim_native/orchestration/perf/telemetry.py` — Already has global_throughput singleton
- `faim_native/orchestration/perf/hot_cache.py` — Already has CacheStats
- `faim_native/orchestration/perf/spec.py` — Already has SpeedBudget profiles
- `faim_native/api/routers/metrics.py` — Scorecard endpoint stays as-is
- `faim_native/api/routers/health.py` — Health/ready endpoints stay as-is
- All auth, tenant, security middleware — Zero changes
- All other dashboard pages — Zero changes

---

## 3. Backend Implementation Detail

### 3.1 Database Migration: `0011_benchmark_samples.sql`

```sql
-- Migration 0011: Benchmark time-series samples
-- Purpose: Store timestamped metric samples for historical benchmark charts.
-- Additive only. No existing table modifications.

CREATE TABLE IF NOT EXISTS benchmark_samples (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   VARCHAR(64) NOT NULL,
    graph_id    VARCHAR(64) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,   -- 'ingest_latency_ms', 'evolve_latency_ms', 'query_latency_ms', 'throughput_sps', etc.
    metric_value DOUBLE PRECISION NOT NULL,
    labels      JSONB DEFAULT '{}',     -- Optional: {"phase": "encode", "endpoint": "/ingest"}
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bs_tenant_graph_metric
    ON benchmark_samples(tenant_id, graph_id, metric_name, recorded_at DESC);

CREATE INDEX idx_bs_recorded_at
    ON benchmark_samples(recorded_at DESC);
```

**Why this schema:**
- `metric_name` is a string enum, not a separate table, to avoid joins
- `labels` JSONB allows per-phase breakdown without extra columns
- `recorded_at DESC` index for fast "latest N samples" queries
- Tenant-isolated by default via composite index

### 3.2 Router: `faim_native/api/routers/benchmarks.py`

Three endpoints:

**Endpoint 1: `GET /api/v1/benchmarks/snapshot?graph_id=X`**
Returns the current benchmark state by aggregating from existing sources:
```python
# Pulls from:
# 1. /metrics/scorecard (D, H, Lambda, R, N, E, node_count, edge_count)
# 2. global_throughput.get_throughput() (synapses/sec)
# 3. HotNodeCache.stats (hit_rate, hits, misses, evictions)
# 4. /ready endpoint (db_connected, tables_ok)
# 5. get_speed_budget() (active profile + targets)
# 6. Latest ingest event for phase_latency_ms
# 7. Latest evolve event for evolve_latency_ms
# 8. Graph stats (node_count, atom_count, macro_count, edge_count, inheritance_edges)
```

Response shape:
```json
{
  "timestamp": "2026-04-09T22:15:30Z",
  "graph_id": "U:abc123",
  "graph_version": 47,

  "fractal_metrics": {
    "D_hat": 2.31,
    "H_hat": 0.74,
    "lambda_hat": 0.52,
    "redundancy_R": 0.08,
    "novelty_N": 0.34,
    "energy_E": 0.89,
    "compression_ratio": 1.42,
    "diagnostics_hash": "abc123..."
  },

  "graph_stats": {
    "node_count": 1247,
    "atom_count": 1180,
    "macro_count": 67,
    "edge_count": 3891,
    "inheritance_edges": 3412
  },

  "performance": {
    "throughput_sps": 142.5,
    "last_ingest_latency_ms": 234,
    "last_ingest_phase_ms": {
      "extract": 45,
      "packetize": 12,
      "encode": 67,
      "write": 89,
      "diagnostics": 21
    },
    "last_evolve_latency_ms": 312,
    "last_evolve_merges": 3,
    "last_evolve_prunes": 1,
    "last_evolve_inventions": 0
  },

  "cache": {
    "hit_rate": 0.87,
    "hits": 4521,
    "misses": 673,
    "evictions": 89,
    "size": 12400
  },

  "speed_budget": {
    "active_profile": "STRICT",
    "p95_insert_target_ms": 25.0,
    "p95_retrieve_target_ms": 10.0,
    "min_insert_qps_target": 50,
    "max_nodes_total": 1000000
  },

  "health": {
    "db_connected": true,
    "tables_ok": true,
    "migrations_ok": true
  },

  "invariants": {
    "inheritance_sum_ok": true,
    "boundedness_ok": true,
    "no_orphan_edges": true,
    "D_range_ok": true,
    "H_range_ok": true,
    "lambda_range_ok": true,
    "energy_bounded_ok": true,
    "all_passed": true,
    "errors": []
  }
}
```

**Endpoint 2: `GET /api/v1/benchmarks/history?graph_id=X&metric=ingest_latency_ms&limit=100`**
Returns time-series data from `benchmark_samples` table.

Response shape:
```json
{
  "metric": "ingest_latency_ms",
  "graph_id": "U:abc123",
  "samples": [
    {"recorded_at": "2026-04-09T22:00:00Z", "value": 234, "labels": {}},
    {"recorded_at": "2026-04-09T21:55:00Z", "value": 198, "labels": {}},
    ...
  ]
}
```

**Endpoint 3: `POST /api/v1/benchmarks/run?graph_id=X`**
Runs a live benchmark: ingests a small synthetic test document, evolves once, queries once, measures all latencies, runs invariant checks, and returns the complete result. This is the "Run Benchmark" button action.

Response shape:
```json
{
  "status": "completed",
  "ingest_benchmark": {
    "latency_ms": 312,
    "nodes_written": 8,
    "merges": 1,
    "phase_ms": {"extract": 42, "packetize": 8, "encode": 112, "write": 134, "diagnostics": 16}
  },
  "evolve_benchmark": {
    "latency_ms": 187,
    "merges": 2,
    "prunes": 0,
    "inventions": 0
  },
  "query_benchmark": {
    "latency_ms": 45,
    "candidates_recalled": 42,
    "results_returned": 10
  },
  "fractal_diagnostics": {
    "D_hat": 2.31, "H_hat": 0.74, "lambda_hat": 0.52,
    "redundancy_R": 0.08, "novelty_N": 0.34, "energy_E": 0.89
  },
  "invariants": {
    "all_passed": true,
    "checks_count": 14,
    "errors": []
  },
  "speed_budget_compliance": {
    "insert_within_p95": true,
    "retrieve_within_p95": true,
    "throughput_above_min": true
  }
}
```

### 3.3 Service: `faim_native/api/services/benchmark_collector.py`

Responsibilities:
- `get_current_snapshot(ctx, graph_id)` → Aggregates from scorecard API, telemetry singleton, cache stats, health check, speed budget, invariants
- `get_metric_history(ctx, graph_id, metric_name, limit)` → Queries benchmark_samples table
- `run_live_benchmark(ctx, graph_id)` → Executes synthetic ingest + evolve + query and measures
- `record_sample(ctx, graph_id, metric_name, value, labels)` → Inserts into benchmark_samples

Key design decisions:
- **Does NOT duplicate existing computation** — calls scorecard, reads telemetry singleton, reads cache stats
- **Invariant checks run on demand** via `check_all_invariants()` + `check_fractal_invariants()` from `core/invariants.py`
- **Live benchmark uses a dedicated test graph_id** (`__benchmark_test__`) to avoid polluting user data
- **Caches snapshot in Redis** with 30s TTL to avoid hammering scorecard on rapid page refreshes

### 3.4 Middleware: `faim_native/api/middleware/latency_collector.py`

Lightweight middleware that:
1. Records `time.monotonic()` at request start
2. Records latency at request end
3. Batches samples into an in-memory buffer (max 100)
4. Flushes buffer to `benchmark_samples` table every 10 seconds or when buffer is full
5. Uses a background thread for DB writes (never blocks request)

**Performance guarantee:** Adds < 1ms per request (two `time.monotonic()` calls + one deque append).

### 3.5 Repository: `faim_native/store/pg/repos/benchmark_repo.py`

```python
class BenchmarkRepo:
    def insert_sample(self, session, tenant_id, graph_id, metric_name, value, labels=None)
    def get_samples(self, session, tenant_id, graph_id, metric_name, limit=100)
    def get_latest(self, session, tenant_id, graph_id, metric_name)
    def cleanup_old(self, session, tenant_id, retention_days=30)
```

---

## 4. Frontend Implementation Detail

### 4.1 Types: `frontend/src/types/benchmarks.ts`

```typescript
export interface FractalMetrics {
  D_hat: number;        // [0, 10] fractal dimension
  H_hat: number;        // [0, 1]  entropy
  lambda_hat: number;   // [0, 1]  evolution pressure
  redundancy_R: number; // [0, 1]  fraction of high-sim pairs
  novelty_N: number;    // [0, 1]  mean residual
  energy_E: number;     // [0, 2]  must stay bounded
  compression_ratio: number;
  diagnostics_hash: string;
}

export interface GraphStats {
  node_count: number;
  atom_count: number;
  macro_count: number;
  edge_count: number;
  inheritance_edges: number;
}

export interface PerformanceMetrics {
  throughput_sps: number;
  last_ingest_latency_ms: number;
  last_ingest_phase_ms: Record<string, number>;
  last_evolve_latency_ms: number;
  last_evolve_merges: number;
  last_evolve_prunes: number;
  last_evolve_inventions: number;
}

export interface CacheMetrics {
  hit_rate: number;
  hits: number;
  misses: number;
  evictions: number;
  size: number;
}

export interface SpeedBudgetInfo {
  active_profile: string;
  p95_insert_target_ms: number;
  p95_retrieve_target_ms: number;
  min_insert_qps_target: number;
  max_nodes_total: number;
}

export interface InvariantStatus {
  inheritance_sum_ok: boolean;
  boundedness_ok: boolean;
  no_orphan_edges: boolean;
  D_range_ok: boolean;
  H_range_ok: boolean;
  lambda_range_ok: boolean;
  energy_bounded_ok: boolean;
  all_passed: boolean;
  errors: string[];
}

export interface BenchmarkSnapshot {
  timestamp: string;
  graph_id: string;
  graph_version: number;
  fractal_metrics: FractalMetrics;
  graph_stats: GraphStats;
  performance: PerformanceMetrics;
  cache: CacheMetrics;
  speed_budget: SpeedBudgetInfo;
  health: { db_connected: boolean; tables_ok: boolean; migrations_ok: boolean };
  invariants: InvariantStatus;
}

export interface BenchmarkHistorySample {
  recorded_at: string;
  value: number;
  labels: Record<string, string>;
}

export interface LiveBenchmarkResult {
  status: string;
  ingest_benchmark: { latency_ms: number; nodes_written: number; merges: number; phase_ms: Record<string, number> };
  evolve_benchmark: { latency_ms: number; merges: number; prunes: number; inventions: number };
  query_benchmark: { latency_ms: number; candidates_recalled: number; results_returned: number };
  fractal_diagnostics: FractalMetrics;
  invariants: InvariantStatus;
  speed_budget_compliance: { insert_within_p95: boolean; retrieve_within_p95: boolean; throughput_above_min: boolean };
}
```

### 4.2 API Client: `frontend/src/lib/benchmarkApi.ts`

```typescript
import { apiGet, apiPost } from "./api-client";
import type { BenchmarkSnapshot, BenchmarkHistorySample, LiveBenchmarkResult } from "@/types/benchmarks";

export async function fetchBenchmarkSnapshot(graphId: string): Promise<BenchmarkSnapshot> {
  return apiGet<BenchmarkSnapshot>(`/benchmarks/snapshot?graph_id=${encodeURIComponent(graphId)}`);
}

export async function fetchBenchmarkHistory(
  graphId: string, metric: string, limit = 100
): Promise<{ metric: string; samples: BenchmarkHistorySample[] }> {
  return apiGet(`/benchmarks/history?graph_id=${encodeURIComponent(graphId)}&metric=${metric}&limit=${limit}`);
}

export async function runLiveBenchmark(graphId: string): Promise<LiveBenchmarkResult> {
  return apiPost<LiveBenchmarkResult>(`/benchmarks/run?graph_id=${encodeURIComponent(graphId)}`);
}
```

### 4.3 Page Layout: `frontend/src/app/(app)/dashboard/benchmarks/page.tsx`

Replace the entire page content. New layout:

```
BenchmarksPage (calls fetchBenchmarkSnapshot on mount, auto-refresh 30s)
├── GlassHeader
│   ├── Title: "Engine Benchmarks"
│   ├── Subtitle: "Live FAIM-Native Performance & Fractal Health"
│   ├── Badge: active SpeedBudget profile name (e.g., "STRICT")
│   ├── Badge: invariant status (green "All Passed" or red "X Errors")
│   └── Button: "Run Benchmark" → calls runLiveBenchmark()
│
├── Metric Strip (4 cards, REAL data)
│   ├── "Throughput" → performance.throughput_sps + " syn/s"
│   ├── "Ingest Latency" → performance.last_ingest_latency_ms + "ms"
│   ├── "Cache Hit Rate" → cache.hit_rate * 100 + "%"
│   └── "Graph Nodes" → graph_stats.node_count (atoms + macros breakdown)
│
├── Grid: 2 columns
│   ├── Left (col-span-3): Fractal Physics Panel
│   │   ├── D_hat gauge (0-10 range, color: complexity)
│   │   ├── H_hat gauge (0-1 range, color: diversity)
│   │   ├── Lambda_hat gauge (0-1 range, color: pressure)
│   │   ├── R gauge (0-1 range, lower=better)
│   │   ├── N gauge (0-1 range, higher=more novel)
│   │   └── E gauge (0-2 range, must stay ≤2)
│   │
│   └── Right (col-span-2): Pipeline Latency Chart
│       ├── Stacked bar chart: ingest phases (extract, packetize, encode, write, diagnostics)
│       ├── Compared against SpeedBudget p95 target (red line)
│       └── Evolve latency bar
│
├── Invariant Status Panel (bottom)
│   ├── inheritance_sum_ok ✓/✗
│   ├── boundedness_ok ✓/✗
│   ├── no_orphan_edges ✓/✗
│   ├── fractal bounds (D, H, Lambda, Energy) ✓/✗
│   └── Error messages if any
│
└── Footer: "Last updated: {timestamp} • Auto-refresh: 30s • Graph version: {version}"
```

### 4.4 Components

**BenchmarkMetricCard.tsx** — Replaces the hardcoded stat cards:
- Props: `{ label, value, unit, subtext, icon, color }`
- Renders real data from snapshot
- Shows loading skeleton while fetching

**FractalPhysicsPanel.tsx** — FAIM-specific:
- Shows all 7 fractal metrics with progress bars and value labels
- Color coding: green (healthy range), amber (warning), red (out of bounds)
- Tooltip explains each metric (e.g., "H_hat: Shannon entropy of similarity distribution. Higher = more diverse graph")

**PipelineLatencyChart.tsx** — Uses recharts (already in package.json):
- Stacked bar chart showing ingest phase breakdown
- Horizontal red line showing SpeedBudget p95 target
- Compares actual vs target

**InvariantStatusPanel.tsx** — Shows FAIM invariant health:
- Grid of invariant checks with pass/fail icons
- Expandable error details if any invariant fails

---

## 5. Implementation Phases

### Phase 1: Backend Data Layer (2 days)
1. Write migration `0011_benchmark_samples.sql`
2. Implement `benchmark_repo.py` (insert, query, cleanup)
3. Implement `latency_collector.py` middleware (lightweight, async flush)
4. Write unit tests for repo
5. **Verify:** Migration runs, no existing table affected, middleware adds <1ms

### Phase 2: Backend API Router (2 days)
1. Implement `benchmark_collector.py` service
2. Implement `routers/benchmarks.py` with 3 endpoints
3. Register router in `app.py` and `__init__.py`
4. Write acceptance tests for all 3 endpoints
5. **Verify:** All endpoints return valid data, tenant isolation enforced, existing APIs unaffected

### Phase 3: Frontend Types & API Client (0.5 day)
1. Create `types/benchmarks.ts`
2. Create `lib/benchmarkApi.ts`
3. **Verify:** TypeScript compiles, types match backend response shapes

### Phase 4: Frontend Page & Components (2 days)
1. Create `BenchmarkMetricCard.tsx`
2. Create `FractalPhysicsPanel.tsx`
3. Create `PipelineLatencyChart.tsx`
4. Create `InvariantStatusPanel.tsx`
5. Rewrite `benchmarks/page.tsx` to use real API calls
6. Add loading states, error boundaries
7. **Verify:** Page loads, shows real data, "Run Benchmark" works, auto-refresh works

### Phase 5: Hardening (1 day)
1. Add loading skeletons
2. Test with no data (empty graph)
3. Test with slow/failed API
4. Add E2E test (Playwright)
5. Retention cleanup job for old benchmark_samples rows
6. **Verify:** No regressions on other pages, benchmarks page works in all scenarios

---

## 6. FAIM-NATIVE BENCHMARK SUITE — Provable Claims Framework

This is what makes FAIM's benchmarks page genuinely state-of-the-art: **a benchmark suite that proves capabilities no competitor can match**, with real numbers, real verification, and real evidence.

### 6.1 The 9 Benchmark Categories (FAIM Proof Suite)

Each category produces a **PASS/FAIL** result with **measurable numbers** that can be displayed on the benchmarks page and exported as proof.

---

#### BM-1: DETERMINISM PROOF
**Claim:** "Same input produces identical output across unlimited reruns."
**No competitor can pass this.** Mem0, Supermemory, Zep, Letta all use ML embeddings with floating-point non-determinism.

**Test procedure:**
1. Ingest document D into fresh graph G1
2. Record: all node vector_hashes, all edge weights, graph_hash, diagnostics_hash
3. Destroy G1 completely
4. Ingest SAME document D into fresh graph G2
5. Record: same measurements
6. **PASS if:** Every vector_hash, graph_hash, and diagnostics_hash is byte-identical between G1 and G2

**Metric displayed:** `Determinism: VERIFIED (100% hash match across N runs)`
**Evidence:** Side-by-side SHA256 hashes from both runs

**Why competitors fail:** Mem0 uses OpenAI embeddings (non-deterministic), Supermemory uses pgvector (float rounding), Zep uses LLM for extraction (temperature > 0).

---

#### BM-2: CRYPTOGRAPHIC INTEGRITY PROOF
**Claim:** "Every piece of stored knowledge has a verifiable integrity chain."
**No competitor offers this.**

**Test procedure:**
1. Ingest 100 documents
2. For each stored vector: recompute `vector_hash` from canonical JSON → compare with stored hash
3. Recompute `graph_hash` from all nodes + edges → compare with stored hash
4. Recompute `diagnostics_hash` from metrics → compare with stored hash
5. **PASS if:** 100% of hashes verify

**Metric displayed:** `Integrity: 100% verified (N vectors, M edges, K diagnostics)`
**Evidence:** Hash verification count + any failures

**Source code proof:** `FAIMVector.verify_hash()` in `encoding/vector_schema.py:217`, `compute_graph_hash()` in `engine_native.py:311`, `compute_diagnostics_hash()` in `fractal_physics.py:492`

---

#### BM-3: MATHEMATICAL INVARIANT PROOF
**Claim:** "8 mathematical invariants hold after every operation, verifiable on demand."
**No competitor has mathematical guarantees.**

**Test procedure:**
1. Ingest 50 documents, run 5 evolve cycles
2. Run `check_all_invariants()` + `check_fractal_invariants()`:
   - Inheritance Sum: for every child node, sum of parent fractions = 1.0 (± 1e-9)
   - Boundedness: no NaN, no Inf in any vector; all norms finite
   - Residual Range: every residual in [0, 1]
   - No Orphan Edges: every edge references existing nodes
   - D Range: fractal dimension in [0, 10]
   - H Range: entropy in [0, 1]
   - Lambda Range: evolution pressure in [0, 1]
   - Energy Bounded: E ≤ 2.0
3. **PASS if:** All 8 invariants hold with zero errors

**Metric displayed:** `Invariants: 8/8 PASSED (N checks, 0 violations)`
**Evidence:** Per-invariant check count and result

**Source code proof:** `invariants.py:207-239` (`check_all_invariants`), `invariants.py:442-475` (`check_fractal_invariants`)

---

#### BM-4: ZERO-LLM OPERATION PROOF
**Claim:** "Core engine operates with zero cloud LLM calls. No API key, no network, no external dependency."
**Only SuperLocalMemory shares this claim. Mem0, Supermemory, Zep, Letta ALL require cloud LLMs.**

**Test procedure:**
1. Disconnect all external network (or run with `FAIM_ENABLE_INDEX=false`, no Qdrant, no external API keys)
2. Ingest 20 documents → verify nodes written
3. Run evolve → verify diagnostics computed
4. Run query → verify results returned with scoring
5. Verify zero HTTP calls to any external service
6. **PASS if:** All operations complete successfully with zero external calls

**Metric displayed:** `Zero-LLM: VERIFIED (ingest + evolve + query completed offline)`
**Evidence:** Network call count = 0, operations completed count

---

#### BM-5: DEDUPLICATION EFFECTIVENESS
**Claim:** "Antisymmetric merge automatically detects and eliminates redundancy at 95% cosine similarity threshold."

**Test procedure:**
1. Create 50 unique documents
2. Create 50 near-duplicate documents (95%+ similar content)
3. Ingest all 100 documents
4. Count: total nodes after ingest, merge events, opposition edges
5. **Measure:** Dedup ratio = merges / duplicates_ingested

**Metric displayed:** `Dedup: X% redundancy eliminated (Y merges from Z duplicates)`
**Evidence:** Node count before/after, merge count, opposition edge count

**Comparison context:** Mem0 has no built-in dedup. Supermemory claims contradiction resolution but no published dedup ratios. Zep has no merge mechanism.

---

#### BM-6: SELF-EVOLUTION PROOF
**Claim:** "Graph self-optimizes via fractal diagnostics without human intervention."
**No competitor has automatic mathematical evolution.**

**Test procedure:**
1. Ingest 100 documents into fresh graph
2. Record initial diagnostics: D₀, H₀, Lambda₀, R₀, N₀, E₀
3. Run 10 evolve cycles automatically
4. Record final diagnostics: D₁₀, H₁₀, Lambda₁₀, R₁₀, N₁₀, E₁₀
5. **Measure:**
   - Redundancy reduction: R₀ → R₁₀ (should decrease or stay stable)
   - Structural evolution: D change, H change
   - Merge + prune + invention counts per cycle
6. **PASS if:** Evolution ran without errors, invariants held throughout, at least one optimization action taken

**Metric displayed:** `Evolution: X merges, Y prunes, Z inventions across N cycles. Redundancy: R₀ → R₁₀`
**Evidence:** Per-cycle diagnostics timeline showing D, H, Lambda, R, N, E trajectory

---

#### BM-7: INGEST PIPELINE PERFORMANCE
**Claim:** "Full ingest pipeline with deterministic encoding, inheritance, and merge in under SpeedBudget p95 targets."

**Test procedure:**
1. Prepare 10 documents of varying sizes (1KB, 10KB, 100KB, 1MB)
2. Ingest each, record:
   - Total latency (ms)
   - Phase breakdown: extract, packetize, encode, write, diagnostics
   - Nodes written, vectors encoded
3. Compute p50, p95, p99 across all ingests
4. Compare against active SpeedBudget profile targets

**Metric displayed:**
```
Ingest p50: Xms | p95: Yms | p99: Zms
SpeedBudget target: {p95_insert_ms_strict}ms
Status: WITHIN TARGET / EXCEEDED TARGET
```
**Evidence:** Per-ingest latency table with phase breakdown

**Comparison context:** Mem0 p95 = 1.44s, Supermemory = sub-300ms, Zep = ~300ms

---

#### BM-8: QUERY FIDELITY
**Claim:** "Physics-based re-ranker produces deterministic, explainable rankings."

**Test procedure:**
1. Ingest 50 diverse documents
2. Run 20 queries with known relevant answers
3. Measure:
   - Precision@K (K=1, 5, 10): how many top-K results are relevant
   - Recall@K: how many relevant results are in top-K
   - Score explainability: verify each result has full score_components breakdown (sim, novel, opp, red, rec, use, lvl)
4. Run same 20 queries again → verify identical rankings (determinism)

**Metric displayed:**
```
Precision@1: X% | P@5: Y% | P@10: Z%
Recall@10: W%
Determinism: 100% (identical rankings across N runs)
```
**Evidence:** Per-query result table with score_components

---

#### BM-9: MULTI-TENANT ISOLATION PROOF
**Claim:** "Cryptographic tenant isolation prevents cross-tenant data leakage."

**Test procedure:**
1. Create Tenant A with 50 documents
2. Create Tenant B with 50 different documents
3. Query from Tenant A → verify ZERO results from Tenant B's documents
4. Query from Tenant B → verify ZERO results from Tenant A's documents
5. Attempt to access Tenant A's metrics from Tenant B's API key → verify 401/403
6. **PASS if:** Zero cross-tenant leakage across all tests

**Metric displayed:** `Tenant Isolation: VERIFIED (0 leaks across N cross-tenant queries)`
**Evidence:** Cross-tenant query count + leak count (must be 0)

---

### 6.2 FAIM Maturity Score (Composite)

Compute a **single maturity score** from the 9 benchmarks:

```
Maturity Score = (
    BM1_determinism * 15 +      (0 or 15)
    BM2_integrity * 15 +         (0 or 15)
    BM3_invariants * 15 +        (0 or 15)
    BM4_zero_llm * 10 +          (0 or 10)
    BM5_dedup * 10 +             (0-10 scaled by dedup %)
    BM6_evolution * 10 +         (0-10 scaled by optimization actions)
    BM7_performance * 10 +       (0-10 scaled by SpeedBudget compliance)
    BM8_query * 10 +             (0-10 scaled by precision/recall)
    BM9_isolation * 5            (0 or 5)
) / 100
```

**Result:** A score from 0-100 that represents FAIM's overall engine maturity.

This replaces the fake "94.2 Maturity Score" on the current page with a **real, verifiable, reproducible number**.

### 6.3 Comparative Claims Table (For Benchmarks Page)

The benchmarks page displays a comparison table based on REAL evidence:

```
╔══════════════════════════════╦══════╦══════╦═══════════╦═════╦═══════╗
║ Capability                   ║ FAIM ║ Mem0 ║ Supermem. ║ Zep ║ Letta ║
╠══════════════════════════════╬══════╬══════╬═══════════╬═════╬═══════╣
║ Deterministic Output         ║  ✓*  ║  ✗   ║     ✗     ║  ✗  ║   ✗   ║
║ Cryptographic Integrity      ║  ✓*  ║  ✗   ║     ✗     ║  ✗  ║   ✗   ║
║ Mathematical Invariants (8)  ║  ✓*  ║  ✗   ║     ✗     ║  ✗  ║   ✗   ║
║ Zero Cloud LLM Dependency    ║  ✓*  ║  ✗   ║     ✗     ║  ✗  ║   ✗   ║
║ Built-in Deduplication       ║  ✓*  ║  ✗   ║     ~     ║  ✗  ║   ✗   ║
║ Self-Evolution               ║  ✓*  ║  ✗   ║     ✗     ║  ✗  ║   ✗   ║
║ Multi-Tenant Crypto Isolation║  ✓*  ║  ~   ║     ✗     ║  ✗  ║   ✗   ║
╠══════════════════════════════╬══════╬══════╬═══════════╬═════╬═══════╣
║ * = Verified by FAIM Proof Suite (click to see evidence)         ║
║ ✗ = Not supported  ~ = Partial support                          ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Critical: Every ✓ in FAIM's column is backed by a real benchmark run with evidence.** Not a marketing claim. The user can click any ✓ to see the actual test results.

### 6.4 What FAIM Cannot Claim (Honest Gaps)

The benchmarks page must also show what FAIM has NOT been tested on:

```
Industry Benchmark Status:
• LOCOMO Score: Not yet tested (adapter in development)
• LongMemEval Score: Not yet tested (adapter in development)
• DMR Score: Not yet tested

These are conversational memory benchmarks that require LLM integration
for evaluation. FAIM's core engine is LLM-independent by design.
A LOCOMO adapter is planned for future work.
```

This honesty builds trust. Competitors who only show numbers where they win are less trustworthy than a system that shows both strengths AND acknowledged gaps.

### 6.5 Implementation: Benchmark Runner

**Backend: `faim_native/api/services/proof_suite_runner.py`**

```python
class ProofSuiteRunner:
    """Runs the 9 FAIM benchmark categories and produces verifiable results."""

    def run_all(self, ctx, graph_id) -> ProofSuiteResult:
        """Run full proof suite. Takes 2-5 minutes."""
        results = {}
        results["BM1_determinism"] = self._run_determinism_proof(ctx, graph_id)
        results["BM2_integrity"] = self._run_integrity_proof(ctx, graph_id)
        results["BM3_invariants"] = self._run_invariant_proof(ctx, graph_id)
        results["BM4_zero_llm"] = self._run_zero_llm_proof(ctx, graph_id)
        results["BM5_dedup"] = self._run_dedup_benchmark(ctx, graph_id)
        results["BM6_evolution"] = self._run_evolution_proof(ctx, graph_id)
        results["BM7_performance"] = self._run_performance_benchmark(ctx, graph_id)
        results["BM8_query"] = self._run_query_fidelity(ctx, graph_id)
        results["BM9_isolation"] = self._run_isolation_proof(ctx, graph_id)
        maturity = self._compute_maturity_score(results)
        return ProofSuiteResult(benchmarks=results, maturity_score=maturity)

    def run_single(self, ctx, graph_id, benchmark_id) -> BenchmarkResult:
        """Run a single benchmark category."""
        ...
```

**Backend endpoint: `POST /api/v1/benchmarks/proof-suite?graph_id=X`**
- Returns streaming SSE progress as each benchmark completes
- Final result includes all 9 categories + maturity score + evidence hashes

**Frontend: `frontend/src/components/benchmarks/ProofSuitePanel.tsx`**
- "Run Proof Suite" button (separate from quick benchmark)
- Shows progress as each of 9 categories completes
- Displays maturity score prominently
- Expandable evidence for each category
- Comparison table with competitors

### 6.6 New Files for Proof Suite

| # | File | Purpose |
|---|------|---------|
| 1 | `faim_native/api/services/proof_suite_runner.py` | Runs 9 benchmark categories |
| 2 | `faim_native/api/services/synthetic_data.py` | Generates deterministic test documents for benchmarks |
| 3 | `frontend/src/components/benchmarks/ProofSuitePanel.tsx` | UI for proof suite execution and results |
| 4 | `frontend/src/components/benchmarks/ComparisonTable.tsx` | Side-by-side competitor comparison |
| 5 | `frontend/src/components/benchmarks/MaturityScoreGauge.tsx` | Large gauge showing composite score |
| 6 | `tests/acceptance/test_AT_proof_suite.py` | Acceptance tests for proof suite |

---

## 7. What Must NOT Break

| System | Protection Strategy |
|--------|-------------------|
| **Existing APIs** | Zero changes to any existing endpoint. New router only. |
| **Existing database tables** | Migration is additive (new table only). No ALTER on existing tables. |
| **Existing middleware** | New middleware is additive. Existing auth, tenant, rate limit, security middleware untouched. |
| **Core engine** | Zero changes to engine_native.py, antisym.py, invariants.py, fractal_physics.py, query_engine.py |
| **Orchestration flows** | Zero changes to ingest_flow.py, evolve_flow.py, query_flow.py. We READ their results, not modify them. |
| **Perf infrastructure** | Zero changes to telemetry.py, hot_cache.py, spec.py. We READ their singletons. |
| **Auth/Security** | Benchmark endpoints use same `get_faim_context` dependency = same tenant isolation + auth checks |
| **Frontend routing** | `/dashboard/benchmarks` route already exists in sidebar. Only page content changes. |
| **Other dashboard pages** | Zero changes to any other page component |

---

## 7. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| `benchmark_samples` table grows unbounded | Medium | Add retention cleanup (30d default) + index for fast deletion |
| Latency middleware adds request overhead | Low | Uses `time.monotonic()` + deque append = <1ms. Async DB flush in background thread. |
| Live benchmark (`/benchmarks/run`) modifies user graph | High | Uses dedicated `__benchmark_test__` graph_id, cleaned up after run. Never touches user data. |
| Scorecard computation is O(n^2) on large graphs | Medium | Already cached in DIAGNOSTICS_SNAPSHOT events. We read events, don't recompute. |
| Frontend shows stale data | Low | 30s auto-refresh + "Last updated" timestamp shown to user. |
| Invariant check is expensive on large graphs | Medium | Run on-demand only (when "Run Benchmark" clicked), not on every page load. |

---

## 8. Testing Strategy

### 8.1 Unit Tests
- `test_benchmark_collector.py` — Test aggregation logic with mocked repos/services
- `test_benchmark_repo.py` — Test insert/query/cleanup with test database

### 8.2 Acceptance Tests
- `test_AT_benchmarks_api_surface.py`:
  - `GET /api/v1/benchmarks/snapshot` returns valid shape with all expected fields
  - `GET /api/v1/benchmarks/history` returns time-series data
  - `POST /api/v1/benchmarks/run` executes and returns valid result
  - Tenant isolation: tenant A cannot see tenant B's benchmark data
  - Auth required: unauthenticated requests return 401

### 8.3 E2E Tests (Playwright)
- Page loads without error
- Metric cards show numeric values (not "undefined" or placeholder text)
- "Run Benchmark" button triggers and shows result
- Auto-refresh updates timestamp

---

## 9. Success Criteria

- [ ] `GET /api/v1/benchmarks/snapshot` returns real D_hat, H_hat, Lambda_hat, R, N, E from actual graph data
- [ ] `GET /api/v1/benchmarks/snapshot` returns real throughput_sps from `global_throughput` singleton
- [ ] `GET /api/v1/benchmarks/snapshot` returns real cache hit_rate from `HotNodeCache.stats`
- [ ] `GET /api/v1/benchmarks/snapshot` returns real invariant check results
- [ ] `POST /api/v1/benchmarks/run` executes a real ingest+evolve+query cycle and measures actual latency
- [ ] Frontend shows all metrics from real API, zero hardcoded values
- [ ] Fractal physics panel shows actual D, H, Lambda, R, N, E with correct ranges
- [ ] Pipeline latency chart shows real phase breakdown compared to SpeedBudget target
- [ ] Invariant status panel shows real pass/fail from `check_all_invariants()`
- [ ] All existing APIs, pages, and workflows continue to work unchanged
- [ ] Tenant isolation enforced on all benchmark endpoints
- [ ] **BM-1 Determinism:** Same document ingested twice produces byte-identical hashes
- [ ] **BM-2 Integrity:** 100% of vector_hash, graph_hash, diagnostics_hash verify
- [ ] **BM-3 Invariants:** All 8 mathematical invariants pass after ingest + evolve
- [ ] **BM-4 Zero-LLM:** Full ingest + evolve + query completes with zero external API calls
- [ ] **BM-5 Dedup:** Near-duplicate documents trigger antisymmetric merge
- [ ] **BM-6 Evolution:** Fractal diagnostics change across evolve cycles, invariants hold throughout
- [ ] **BM-7 Performance:** Ingest latency within SpeedBudget p95 targets
- [ ] **BM-8 Query:** Deterministic re-ranking with full score_components explanation
- [ ] **BM-9 Isolation:** Zero cross-tenant data leakage across all tests
- [ ] **Maturity Score:** Composite score computed from all 9 benchmarks, displayed prominently
- [ ] **Comparison Table:** Side-by-side with Mem0/Supermemory/Zep showing verified capabilities

---

## 10. STATE-OF-THE-ART ADDITIONS (Level 3)

Everything above (Sections 1-9) is the **solid foundation**. The following additions elevate the benchmark system to state-of-the-art. These are organized as additional phases that build on top of the foundation.

### 10.1 Live SSE Streaming Benchmarks

**Why:** State-of-the-art observability means REAL-TIME, not polling every 30 seconds. FAIM already has an SSE event stream (`api/routers/events.py`). We extend the same pattern.

**What:**
- New SSE endpoint: `GET /api/v1/benchmarks/stream?graph_id=X`
- Streams benchmark events in real-time as they happen:
  - Every API request → `{type: "latency", endpoint: "/ingest", value_ms: 234, ts: "..."}`
  - Every evolve cycle → `{type: "evolve_complete", merges: 3, latency_ms: 187, ts: "..."}`
  - Every diagnostics snapshot → `{type: "diagnostics", D: 2.31, H: 0.74, ...}`
  - Cache stats update → `{type: "cache_update", hit_rate: 0.87, ...}`
  - Throughput update → `{type: "throughput", sps: 142.5, ts: "..."}`
- Frontend: Replace polling with `EventSource` connection. Charts update instantly as events arrive.
- Uses existing SSE pattern from `api/routers/events.py` — consistent with FAIM's event-driven architecture.

**Implementation:**
- Backend: `faim_native/api/routers/benchmarks.py` adds `/stream` SSE endpoint
- Frontend: `frontend/src/lib/benchmarkStream.ts` — EventSource wrapper with reconnection
- Frontend: Charts use streaming data buffer (last 100 points, sliding window)

**Files:**
- Update: `faim_native/api/routers/benchmarks.py` (add SSE endpoint)
- New: `frontend/src/lib/benchmarkStream.ts` (EventSource client)
- Update: `frontend/src/app/(app)/dashboard/benchmarks/page.tsx` (connect to stream)

### 10.2 Progressive Stress Testing (Built Into UI)

**Why:** State-of-the-art benchmarks don't just show current performance — they let you **stress test** the system and find breaking points. This is how teams like Google (Perfkit), Netflix (ChAP), and Uber (BURT) benchmark.

**What:**
- "Stress Test" button on benchmarks page
- User selects: document count (10, 50, 100, 500), concurrency (1, 5, 10), profile (STRICT, FAST, RELAXED)
- Backend runs progressive load:
  1. Ingest N synthetic documents sequentially, measuring each
  2. Ingest N synthetic documents in parallel batches
  3. Run M evolve cycles
  4. Run K queries
  5. After each batch: measure latency, throughput, D/H/Lambda shift, invariant status, memory usage
- Real-time results streamed via SSE as test progresses
- Final report: latency percentiles (p50/p95/p99), throughput curve, at what load invariants break, memory high-water mark

**Frontend visualization:**
- Throughput curve chart: X = concurrency, Y = req/sec (shows saturation point)
- Latency distribution chart: histogram of latency values at each load level
- Fractal stability chart: D/H/Lambda values as load increases (shows when graph destabilizes)
- Pass/fail matrix: which SpeedBudget targets were met at each load level

**Implementation:**
- Backend: `faim_native/api/services/stress_runner.py` — orchestrates progressive load test
- Backend: `POST /api/v1/benchmarks/stress` — starts stress test, returns job_id
- Backend: `GET /api/v1/benchmarks/stress/{job_id}/stream` — SSE stream of progress
- Frontend: `frontend/src/components/benchmarks/StressTestPanel.tsx` — UI for configuring and watching
- Frontend: `frontend/src/components/benchmarks/ThroughputCurveChart.tsx` — recharts line chart
- Frontend: `frontend/src/components/benchmarks/LatencyDistributionChart.tsx` — recharts histogram

**Safety:**
- Stress tests use dedicated `__stress_test__` graph_id, isolated from user data
- Cleanup after completion (delete test graph)
- Rate-limited: max 1 stress test per tenant at a time
- Timeout: max 5 minutes per stress test
- Respects Docker resource limits (2 CPU, 1G RAM)

### 10.3 Google Golden Signals Dashboard

**Why:** Google SRE's "Four Golden Signals" (Latency, Traffic, Errors, Saturation) is the industry standard for production monitoring. State-of-the-art benchmarks frame everything through these signals.

**What:**

| Golden Signal | FAIM Mapping | Source |
|---------------|-------------|--------|
| **Latency** | Ingest p50/p95/p99, Evolve latency, Query latency | `benchmark_samples` table + latency_collector middleware |
| **Traffic** | Requests/sec per endpoint, Synapses/sec (throughput) | `global_throughput` singleton + middleware counter |
| **Errors** | 5xx rate, 4xx rate, Invariant violations, Failed evolve cycles | Middleware error counter + invariant checks |
| **Saturation** | CPU usage, Memory usage, DB connection pool utilization, Cache capacity, Nodes vs max_nodes_total | Docker stats API + PostgreSQL `pg_stat_activity` + Redis `INFO` + SpeedBudget limits |

**Implementation:**
- Backend: `GET /api/v1/benchmarks/golden-signals?graph_id=X` returns all 4 signals in one response
- For **Saturation**: query container metrics via Docker socket OR `/proc/self/status` for memory, `os.cpu_count()` + `psutil.cpu_percent()` for CPU
- For **DB Saturation**: `SELECT count(*) FROM pg_stat_activity` vs connection pool max
- For **Cache Saturation**: `HotNodeCache.stats.size` / `HotNodeCache.max_size`
- For **Node Saturation**: `node_count` / `SpeedBudget.max_nodes_total`

**Frontend:**
- 4-panel golden signals display at the top of benchmarks page
- Each panel shows: current value, trend arrow (up/down/stable), sparkline (last 1h)
- Color coding: green (healthy), amber (>70% of limit), red (>90% of limit or error spike)

### 10.4 Comparative Baselines & Regression Detection

**Why:** State-of-the-art means not just "what is performance NOW" but "is it better or worse than BEFORE?" Systems like Continuous Profiling (Google), Parca, and DataDog APM all do this.

**What:**
- On every `POST /api/v1/benchmarks/run`, save the result as a **baseline snapshot** in `benchmark_baselines` table
- Show comparison: current vs last baseline, current vs best-ever baseline
- Auto-detect regressions: if latency increased >20% vs last 7-day average, flag as regression
- Show delta arrows on every metric card: +12ms (red), -8ms (green)

**Implementation:**
- New table: `benchmark_baselines` (stores full benchmark results with version tag)
- Backend: `benchmark_collector.py` adds `compare_to_baseline(current, baseline)` method
- Frontend: `BenchmarkMetricCard.tsx` gets optional `delta` prop showing change from baseline
- Frontend: `BaselineComparisonPanel.tsx` — side-by-side comparison table

**Migration:**
```sql
-- 0012_benchmark_baselines.sql
CREATE TABLE IF NOT EXISTS benchmark_baselines (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   VARCHAR(64) NOT NULL,
    graph_id    VARCHAR(64) NOT NULL,
    label       VARCHAR(128) NOT NULL,  -- 'auto_2026-04-09', 'manual_v1.0_release'
    snapshot    JSONB NOT NULL,          -- Full BenchmarkSnapshot JSON
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_bb_tenant_graph ON benchmark_baselines(tenant_id, graph_id, created_at DESC);
```

### 10.5 Container & Infrastructure Telemetry

**Why:** FAIM runs in Docker with resource limits (2 CPU, 1G RAM). State-of-the-art benchmarks show infrastructure-level metrics alongside application metrics — so you know if a latency spike is because of your code or because the container hit its memory ceiling.

**What:**
- **CPU %**: From `/proc/self/stat` or `psutil.cpu_percent()` (already optionally available in spec.py)
- **Memory**: From `/proc/self/status` (VmRSS, VmPeak) or `psutil.virtual_memory()` 
- **PostgreSQL**: Active connections (`pg_stat_activity`), DB size (`pg_database_size`), slow queries
- **Redis**: `INFO` command → memory_used, connected_clients, keyspace_hits/misses, evicted_keys
- **Qdrant** (if enabled): Collection info, point count, search latency

**Implementation:**
- Backend: `faim_native/api/services/infra_telemetry.py`
  - `get_process_metrics()` → CPU%, memory RSS, memory peak
  - `get_postgres_metrics(session)` → active connections, DB size, table sizes
  - `get_redis_metrics(cache)` → memory, clients, hit rate, evictions
  - `get_qdrant_metrics(index)` → collection info, points, search latency
- Included in `GET /api/v1/benchmarks/snapshot` response under `infrastructure` key
- Frontend: `InfrastructurePanel.tsx` showing resource gauges

**Response addition:**
```json
{
  "infrastructure": {
    "process": {
      "cpu_percent": 45.2,
      "memory_rss_mb": 412,
      "memory_peak_mb": 523
    },
    "postgres": {
      "active_connections": 12,
      "max_connections": 100,
      "db_size_mb": 234,
      "tables": {"nodes": 89, "edges": 112, "events": 23}
    },
    "redis": {
      "memory_used_mb": 34,
      "connected_clients": 8,
      "keyspace_hit_rate": 0.94,
      "evicted_keys": 0
    },
    "qdrant": null,
    "docker": {
      "cpu_limit": 2.0,
      "memory_limit_mb": 1024,
      "cpu_utilization_percent": 22.6,
      "memory_utilization_percent": 40.2
    }
  }
}
```

### 10.6 Exportable Benchmark Reports

**Why:** State-of-the-art systems (MLPerf, TPC benchmarks, SPEC) produce exportable, reproducible benchmark reports. This is critical for compliance, auditing, and sharing with stakeholders.

**What:**
- "Export Report" button on benchmarks page
- Generates a structured JSON report with:
  - System info (FAIM version, SpeedBudget profile, Docker resources, PostgreSQL version)
  - All current metrics (fractal physics, performance, cache, invariants)
  - Historical trend (last 24h averages)
  - Stress test results (if run)
  - Baseline comparison
  - Invariant verification results
  - Timestamp and deterministic hash of the report for integrity
- Report hash is SHA256 of canonical JSON (same pattern as FAIM's existing diagnostics_hash)

**Implementation:**
- Backend: `POST /api/v1/benchmarks/export?graph_id=X` → returns JSON report
- Frontend: "Export Report" button triggers download of JSON file
- Optional: Render report as a styled printable HTML page (using existing GlassHeader + card patterns)

### 10.7 Anomaly Detection (Simple, Rule-Based)

**Why:** State-of-the-art observability includes automated anomaly detection. We keep it simple and deterministic (no ML, consistent with FAIM's philosophy).

**What:**
- Define threshold rules based on SpeedBudget targets:
  - Alert if `ingest_latency > 2x SpeedBudget.p95_insert_ms_strict`
  - Alert if `cache_hit_rate < 0.5`
  - Alert if `energy_E > 1.8` (approaching invariant bound of 2.0)
  - Alert if `redundancy_R > 0.5` (too much duplication, evolve needed)
  - Alert if `error_rate > 0.05` (5% error threshold)
  - Alert if `memory_utilization > 0.85` (85% of container limit)
- Show alerts as colored badges on the benchmarks page
- Store alert history in `benchmark_samples` with metric_name `alert_*`

**Implementation:**
- Backend: `faim_native/api/services/benchmark_alerts.py` — rule engine
- Frontend: `AlertsBanner.tsx` — shows active alerts at top of benchmarks page
- No external dependencies — pure Python rules, consistent with FAIM's "NO ML" philosophy

---

## 11. State-of-the-Art Page Layout (Updated)

```
BenchmarksPage (SSE stream connection + 30s fallback poll)
│
├── AlertsBanner (if any anomalies detected)
│   └── "Ingest latency 2.1x above p95 target" [yellow warning]
│
├── GlassHeader
│   ├── Title: "Engine Benchmarks"
│   ├── Subtitle: "Live FAIM-Native Performance & Fractal Health"
│   ├── Badges: [SpeedBudget profile] [Invariants status] [Graph version]
│   └── Actions: [Run Benchmark] [Stress Test] [Export Report]
│
├── Golden Signals Strip (4 cards)
│   ├── Latency: p95 ingest latency + sparkline + delta from baseline
│   ├── Traffic: req/sec + synapses/sec + sparkline
│   ├── Errors: error rate % + sparkline + alert if >5%
│   └── Saturation: highest utilization gauge (CPU/Mem/DB/Cache)
│
├── Tab Navigation: [Fractal Physics | Pipeline | Infrastructure | History | Stress Test]
│
├── Tab: Fractal Physics (default)
│   ├── 7 metric gauges: D, H, Lambda, R, N, E, CR
│   ├── Color bands: green (healthy) → amber (warning) → red (violation)
│   ├── Each gauge shows: current value, valid range, delta from baseline
│   └── Tooltip: explains what each metric means in FAIM context
│
├── Tab: Pipeline
│   ├── Stacked bar: ingest phase breakdown (extract, packetize, encode, write, diagnostics)
│   ├── Red line: SpeedBudget p95 target
│   ├── Evolve latency bar with merges/prunes/inventions breakdown
│   ├── Query latency bar with recall/rerank breakdown
│   └── Comparison: actual vs SpeedBudget targets (pass/fail indicators)
│
├── Tab: Infrastructure
│   ├── CPU gauge: actual vs Docker limit (2 CPU)
│   ├── Memory gauge: RSS vs Docker limit (1G)
│   ├── PostgreSQL: connections, DB size, table sizes
│   ├── Redis: memory, hit rate, evictions
│   ├── Qdrant: points, search latency (if enabled)
│   └── Cache: HotNodeCache size vs max_warm_nodes
│
├── Tab: History
│   ├── Time-series chart: selectable metric (latency, throughput, D, H, etc.)
│   ├── Time range selector: 1h, 6h, 24h, 7d, 30d
│   ├── Overlay: baseline comparison line (if baseline exists)
│   └── Anomaly markers: red dots where threshold was exceeded
│
├── Tab: Stress Test
│   ├── Config: document count, concurrency, profile
│   ├── Start button → shows real-time progress via SSE
│   ├── Throughput curve: X=concurrency, Y=req/sec
│   ├── Latency distribution: histogram at each load level
│   ├── Fractal stability: D/H/Lambda/E drift under load
│   └── Result summary: SpeedBudget compliance matrix
│
├── Invariant Status Panel
│   ├── 8 invariant checks with pass/fail indicators
│   ├── Expandable error details
│   └── "Last verified: {timestamp}"
│
└── Footer: "Connected via SSE • Graph: {graph_id} • Version: {version} • Profile: {profile}"
```

---

## 12. Updated Implementation Phases (Full)

### Phase 1: Backend Data Layer (2 days) — Foundation
- Migration `0011_benchmark_samples.sql`
- `benchmark_repo.py`
- `latency_collector.py` middleware
- Unit tests

### Phase 2: Backend API Router (2 days) — Foundation
- `benchmark_collector.py` service
- `routers/benchmarks.py` (snapshot, history, run)
- Acceptance tests

### Phase 3: Frontend Foundation (2.5 days) — Foundation
- `types/benchmarks.ts`
- `lib/benchmarkApi.ts`
- `BenchmarkMetricCard.tsx`, `FractalPhysicsPanel.tsx`, `PipelineLatencyChart.tsx`, `InvariantStatusPanel.tsx`
- Rewrite `benchmarks/page.tsx`
- Loading states, error boundaries

### Phase 4: Golden Signals + Infrastructure Telemetry (2 days) — State of the Art
- `infra_telemetry.py` service (CPU, memory, Postgres, Redis, Qdrant)
- `GET /api/v1/benchmarks/golden-signals` endpoint
- `GoldenSignalsStrip.tsx` component
- `InfrastructurePanel.tsx` component

### Phase 5: Live SSE Streaming (1.5 days) — State of the Art
- SSE endpoint: `GET /api/v1/benchmarks/stream`
- `benchmarkStream.ts` EventSource client
- Connect charts to live stream
- Fallback to polling if SSE disconnects

### Phase 6: Stress Testing (2 days) — State of the Art
- `stress_runner.py` service
- `POST /api/v1/benchmarks/stress` + SSE progress stream
- `StressTestPanel.tsx`, `ThroughputCurveChart.tsx`, `LatencyDistributionChart.tsx`
- Safety: isolated graph, timeout, rate limit

### Phase 7: Baselines + Regression Detection (1.5 days) — State of the Art
- Migration `0012_benchmark_baselines.sql`
- Baseline save/compare logic in `benchmark_collector.py`
- `BaselineComparisonPanel.tsx`
- Delta arrows on metric cards

### Phase 8: Anomaly Detection + Export (1 day) — State of the Art
- `benchmark_alerts.py` rule engine
- `AlertsBanner.tsx`
- `POST /api/v1/benchmarks/export` endpoint
- "Export Report" button (JSON download)

### Phase 9: Hardening & E2E (1 day) — Final
- Tab navigation
- E2E tests (Playwright)
- Empty state, error state, slow network
- Retention cleanup
- Documentation

### Phase 10: FAIM Proof Suite (3 days) — Competitive Proof
1. `proof_suite_runner.py` — 9 benchmark categories
2. `synthetic_data.py` — deterministic test document generator
3. `POST /api/v1/benchmarks/proof-suite` endpoint with SSE progress
4. `ProofSuitePanel.tsx` — run + display results
5. `ComparisonTable.tsx` — side-by-side with competitors
6. `MaturityScoreGauge.tsx` — composite maturity score
7. Acceptance tests for proof suite

**Total: ~19 days for full state-of-the-art with competitive proofs**
**Minimum viable (Phases 1-3): ~7 days for real data foundation**
**Proof of superiority (Phases 1-3 + 10): ~10 days for provable claims**

---

## 13. What Makes This State-of-the-Art vs. Competitors

| Feature | Typical Dashboard | Our Implementation |
|---------|-------------------|-------------------|
| Data source | Fake/placeholder | REAL from FAIM engine, PostgreSQL, Redis, Docker |
| Update mechanism | Manual refresh | SSE live streaming with fallback polling |
| Metrics framework | Generic (latency only) | FAIM-specific fractal physics (D, H, Lambda, R, N, E) + Google Golden Signals |
| Stress testing | External tool (JMeter/k6) | Built-in, configured from UI, streams results |
| Baseline comparison | None | Automatic save + delta visualization |
| Anomaly detection | External (PagerDuty/Datadog) | Built-in rule engine, consistent with FAIM's "NO ML" philosophy |
| Infrastructure telemetry | Separate Grafana dashboard | Integrated: CPU, memory, Postgres, Redis, Docker limits |
| Invariant verification | None | 8 mathematical invariants verified live (inheritance sum, boundedness, fractal ranges, energy) |
| Exportable reports | None | Deterministic JSON report with SHA256 integrity hash |
| Container awareness | None | Shows Docker resource limits vs actual usage, saturation alerts |
| Speed budget compliance | None | Real-time comparison against 7 named SpeedBudget profiles with p95 targets |

---

## 14. New File Inventory (Complete, All Phases)

### Backend New Files

| # | File | Phase |
|---|------|-------|
| 1 | `faim_native/store/pg/migrations/0011_benchmark_samples.sql` | 1 |
| 2 | `faim_native/store/pg/repos/benchmark_repo.py` | 1 |
| 3 | `faim_native/api/middleware/latency_collector.py` | 1 |
| 4 | `faim_native/api/services/benchmark_collector.py` | 2 |
| 5 | `faim_native/api/routers/benchmarks.py` | 2 |
| 6 | `faim_native/api/services/infra_telemetry.py` | 4 |
| 7 | `faim_native/api/services/stress_runner.py` | 6 |
| 8 | `faim_native/store/pg/migrations/0012_benchmark_baselines.sql` | 7 |
| 9 | `faim_native/api/services/benchmark_alerts.py` | 8 |
| 10 | `tests/acceptance/test_AT_benchmarks_api_surface.py` | 2 |
| 11 | `tests/unit/test_benchmark_collector.py` | 2 |
| 12 | `tests/unit/test_benchmark_alerts.py` | 8 |

### Frontend New Files

| # | File | Phase |
|---|------|-------|
| 1 | `frontend/src/types/benchmarks.ts` | 3 |
| 2 | `frontend/src/lib/benchmarkApi.ts` | 3 |
| 3 | `frontend/src/lib/benchmarkStream.ts` | 5 |
| 4 | `frontend/src/components/benchmarks/BenchmarkMetricCard.tsx` | 3 |
| 5 | `frontend/src/components/benchmarks/FractalPhysicsPanel.tsx` | 3 |
| 6 | `frontend/src/components/benchmarks/PipelineLatencyChart.tsx` | 3 |
| 7 | `frontend/src/components/benchmarks/InvariantStatusPanel.tsx` | 3 |
| 8 | `frontend/src/components/benchmarks/GoldenSignalsStrip.tsx` | 4 |
| 9 | `frontend/src/components/benchmarks/InfrastructurePanel.tsx` | 4 |
| 10 | `frontend/src/components/benchmarks/StressTestPanel.tsx` | 6 |
| 11 | `frontend/src/components/benchmarks/ThroughputCurveChart.tsx` | 6 |
| 12 | `frontend/src/components/benchmarks/LatencyDistributionChart.tsx` | 6 |
| 13 | `frontend/src/components/benchmarks/BaselineComparisonPanel.tsx` | 7 |
| 14 | `frontend/src/components/benchmarks/AlertsBanner.tsx` | 8 |

### Modified Files (Same as before)

| # | File | Phase |
|---|------|-------|
| 1 | `faim_native/api/app.py` | 2 |
| 2 | `faim_native/api/routers/__init__.py` | 2 |
| 3 | `frontend/src/app/(app)/dashboard/benchmarks/page.tsx` | 3 |

---

## 15. Next Steps

1. **Review & Approve** this plan
2. **Choose scope:** Full state-of-the-art (Phases 1-9) or foundation first (Phases 1-3)?
3. **Phase 1 kickoff** upon approval

---

**Status:** AWAITING APPROVAL — No code written. Review plan and approve before implementation begins.

