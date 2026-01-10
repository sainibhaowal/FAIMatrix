# FAIM Speed Spec (P4.0 — HyperSpeed Contract)

Version: 1.0  
Status: Locked for P3+P4 work  
Owner: FAIM Core (Ravin)  

FAIM is **not** a vector DB. It is a **Fractal Inheritance Graph** with antisymmetric opposition and self-evolution, and the speed layer must respect that identity. :contentReference[oaicite:0]{index=0}

This document defines hard speed and memory contracts for FAIM’s P4 “HyperSpeed” track:  
what “super lightning fast” actually means on laptop and server profiles, and which operations are allowed on the hot path. :contentReference[oaicite:1]{index=1}

---

## 0. Scope & Non-Goals

**In scope**

- Latency and throughput targets for:
  - `retrieve(graph_id, query, k)`
  - steady-state `add_memory(graph_id, payload, meta)` :contentReference[oaicite:2]{index=2}
- RAM budgets for:
  - Hot vectors (Tier-1)
  - Warm NodeRecord cache (Tier-2)
- Disk/GC invariants:
  - What is *never* allowed in the hot path.
- Mapping to speed profiles:
  - `DEV`, `PROD_LAPTOP`, `PROD_SERVER`, `BANK`.

**Out of scope**

- Exact algorithmic details of inheritance / antisym / evolution (covered in `FAIM_Design.md` and engine docs). :contentReference[oaicite:3]{index=3}  
- UI performance (handled in frontend specs).
- Detailed benchmarking datasets (covered in `benchmarks.py` / P6). :contentReference[oaicite:4]{index=4}

---

## 1. TRUE FAIM Speed Principles

These are **laws**, not suggestions:

1. **FAIM ≠ vectors**  
   - FAIM = Graph + Fractal Inheritance + Antisymmetry.  
   - Vectors are only the *physical state* of nodes, not “the memory” itself. :contentReference[oaicite:5]{index=5}  

2. **No raw RAG**  
   - Retrieval is **graph-aware** (`inheritance`, `lineage_expansion`, antisymmetric scoring), not flat K-NN. :contentReference[oaicite:6]{index=6}  

3. **Hot path = pure linear algebra**  
   - Real-time reads/writes only touch:
     - Tier-1: contiguous vector arrays (CPU/GPU).
     - Tier-2: in-RAM NodeRecord cache for returned IDs.
   - No SQLite queries, no JSON parsing, no disk syncs in hot path. :contentReference[oaicite:7]{index=7}  

4. **Disk is shadow, not body**  
   - Tier-3 (NVMe/SSD) is used only for:
     - Snapshots,
     - Journals,
     - Background flushes.
   - Queries must remain within SLA *even if disk is slow*.

5. **Pluggable engines, stable FAIM API**  
   - `FAIMEngine` API remains stable across:
     - CPU-only laptop,
     - GPU server cluster.
   - Backends (FAISS/HNSW, etc.) are plugins inside `faim/speed/`, not FAIM’s identity. :contentReference[oaicite:8]{index=8}  

---

## 2. Speed Profiles

Profiles are controlled via env / config:

- `FAIM_SPEED_PROFILE=DEV|LAPTOP|SERVER|BANK`  
- Optional flags:
  - `FAIM_USE_GPU=true|false`
  - `FAIM_MAX_WARM_NODES=<int>`  
  - `FAIM_PERSIST_MODE=strict|relaxed` (BANK defaults to `strict`). :contentReference[oaicite:9]{index=9}  

Default embedding assumptions:

- Embedding dim `D_default = 64` (allowed: 64–128).
- Vector dtype: `float32`.
- Vector RAM ≈ `N * D * 4` bytes. For 10M nodes @ 64d: ~2.56 GB. :contentReference[oaicite:10]{index=10}  

### 2.1 Profile Summary Table

| Profile       | Target env          | Max graphs | Max nodes total | Max nodes / graph | Hot vector RAM (approx) | Warm cache nodes (Tier-2) |
|---------------|---------------------|------------|-----------------|-------------------|--------------------------|---------------------------|
| DEV           | Single laptop dev   | 1–3        | 1M              | 500k              | ≤ 2 GB                   | 50k                       |
| PROD_LAPTOP   | Personal FAIM       | 1–3        | 10M             | 10M               | ≤ 6 GB (4–8 configurable) | 200k                      |
| PROD_SERVER   | Shared SaaS node    | ≤ 8        | 80M             | 20M               | ≤ 64 GB                  | 500k–1M                   |
| BANK          | Regulated / audit   | ≤ 8        | 80M             | 20M               | ≤ 64 GB                  | 500k–1M                   |

> Note: Vector RAM numbers assume `D=64`. Using `D=128` halves max nodes at the same RAM ceiling unless explicitly raised.

---

## 3. Latency & Throughput Targets

All latency numbers are **server-side** (FAIM engine only, without network).

We track `p50`, `p95`, and optionally `p99` over rolling windows via `core/metrics.py` + `scripts/benchmarks.py`. :contentReference[oaicite:11]{index=11}  

### 3.1 Retrieve (`retrieve(graph_id, query, k)`)

**Single-tenant laptop (PROD_LAPTOP, main graph)**

- 1M nodes:
  - `p95(retrieve) < 2 ms`
- 10M nodes:
  - `p95(retrieve) < 10 ms`

These are measured for `k ≤ 64`, using VectorBank top-K search (single matmul + partial sort). :contentReference[oaicite:12]{index=12}  

**DEV**

- 1M nodes:
  - `p95(retrieve) < 5 ms` (looser, debug builds allowed)
- 300k nodes:
  - `p95(retrieve) < 3 ms`

**PROD_SERVER**

- 10M nodes / graph:
  - `p95(retrieve) < 3 ms`
- 80M nodes total:
  - `p95(retrieve) < 15 ms` for any graph.

**BANK**

- 10M nodes / graph:
  - `p95(retrieve) < 5 ms`
- 80M nodes total:
  - `p95(retrieve) < 20 ms`  
  - `p99(retrieve) < 40 ms` (durability overhead allowed).

### 3.2 Insert (`add_memory` steady state)

Measured under mixed read/write load (e.g. 80% reads, 20% writes):

- **PROD_LAPTOP**
  - At 1–10M nodes:
    - ≥ 100 inserts / second
    - While `p95(retrieve)` stays within profile budgets above. :contentReference[oaicite:13]{index=13}  

- **DEV**
  - ≥ 50 inserts / second.

- **PROD_SERVER**
  - ≥ 500 inserts / second (aggregated across graphs).

- **BANK**
  - ≥ 200 inserts / second (durability overhead allowed).

Latency for `add_memory` is measured as **client-visible completion time** under:

- `FAIM_PERSIST_MODE=relaxed`:
  - Hot work (embed + inheritance + antisym + VectorBank + HotCache) must complete within **5 ms** on laptop for typical payloads.
- `FAIM_PERSIST_MODE=strict` (BANK):
  - Budget is **20 ms** including blocking until current write batch is flushed.

---

## 4. Memory Ceilings

### 4.1 Hot Tier (VectorBank)

For each profile, enforce:

- Total vector RAM ≤ `HOT_RAM_BYTES`.
- When limit is hit:
  - Either reject new inserts (DEV only) or
  - Trigger **vector compaction** / evolution heuristics (P3+P4.1+P4.3) to reclaim memory.

### 4.2 Warm Tier (NodeRecord cache)

- `MAX_WARM_NODES` is enforced via LRU/ARC in `faim/speed/hot_cache.py`. :contentReference[oaicite:14]{index=14}  
- Eviction **never** deletes data; it only drops the in-RAM copy:
  - Node remains in durable store (Tier-3).
  - On next access, loaded once then re-cached.

### 4.3 Cold Tier (NVMe / Snapshot + Journal)

P4.3 moves SQLite/LMDB fully off the hot path: :contentReference[oaicite:15]{index=15}  

- Background snapshot + journal replay handle crash recovery.
- Cold tier size is governed by:
  - Retention windows,
  - Compression,
  - External governance policies (not part of this spec).

---

## 5. Hot Path Invariants

These apply to all profiles unless a stricter rule is configured.

1. **No disk I/O on query path**
   - `retrieve` and the hot portion of `add_memory` must not:
     - Run SQL,
     - Touch LMDB/RocksDB,
     - Read from filesystem.

2. **No JSON encoding/decoding in hot loop**
   - Node metadata used during scoring should live in structs / dataclasses, not JSON blobs.

3. **No full GC pauses in hot loop**
   - Python GC must be configured such that:
     - Full collection is never triggered by a single request,
     - Or GC is disabled for hot threads and run in a dedicated maintenance window.

4. **All math executed in contiguous blocks**
   - Vector ops must be expressed as:
     - `matrix @ vector`, `batched_norms`, or equivalent BLAS/cuBLAS calls.
   - Python loops over nodes are allowed *only* for small `k` (e.g., final scoring) after ANN/VectorBank filtering.

5. **Determinism**
   - Given the same:
     - graph state,
     - config,
     - journal,
   - The sequence of `add_memory` + `retrieve` calls must yield identical results (no hidden randomness).

---

## 6. Observability & Metrics

Metrics are exposed via `core/metrics.py` and `/metrics` endpoint and logged to JSON by `benchmarks.py`. :contentReference[oaicite:16]{index=16}  

Per profile, we track:

- `faim_retrieve_p50_ms`, `faim_retrieve_p95_ms`, `faim_retrieve_p99_ms`
- `faim_insert_p50_ms`, `faim_insert_p95_ms`
- `faim_insert_qps`
- `faim_nodes_total`, `faim_nodes_per_graph`
- `faim_hot_ram_bytes`, `faim_warm_nodes`
- Compression & redundancy:
  - `CR = raw_bytes / faim_bytes`
  - `R` redundancy index (from `metrics.py`). :contentReference[oaicite:17]{index=17}  

A Speed Profile is **violated** if any of:

- Latency metric exceeds its threshold for > 1% of windows.
- Node count exceeds `max_nodes_total` or `max_nodes_per_graph`.
- Hot RAM exceeds budget for more than a configurable grace window (e.g. 60 seconds).

---

## 7. Profile Definitions (Normative)

### 7.1 DEV

- Goal: Developer laptop, debug builds, experiments.
- Constraints:
  - `max_nodes_total = 1_000_000`
  - `max_nodes_per_graph = 500_000`
  - `hot_ram_bytes ≤ 2 * 1024^3`
  - `max_warm_nodes = 50_000`
  - `p95(retrieve @ 1M nodes) < 5 ms`
  - `insert_qps ≥ 50`

### 7.2 PROD_LAPTOP

- Goal: Personal FAIM on a single machine, investor demo, OmniSync integration.
- Constraints:
  - `max_nodes_total = 10_000_000`
  - `max_nodes_per_graph = 10_000_000`
  - `hot_ram_bytes ≤ 6 * 1024^3` (configurable 4–8 GB)
  - `max_warm_nodes = 200_000`
  - `p95(retrieve @ 1M) < 2 ms`
  - `p95(retrieve @ 10M) < 10 ms`
  - `insert_qps ≥ 100`

### 7.3 PROD_SERVER

- Goal: Multi-tenant FAIM Lab / SaaS.
- Constraints:
  - `max_graphs = 8`
  - `max_nodes_total = 80_000_000`
  - `max_nodes_per_graph = 20_000_000`
  - `hot_ram_bytes ≤ 64 * 1024^3`
  - `max_warm_nodes ∈ [500_000, 1_000_000]`
  - `p95(retrieve @ 10M) < 3 ms`
  - `p95(retrieve @ 80M total) < 15 ms`
  - `insert_qps ≥ 500`

### 7.4 BANK

- Goal: Regulated deployments with strict durability and audit trails.
- Constraints:
  - Same node and RAM limits as `PROD_SERVER`.
  - `FAIM_PERSIST_MODE=strict` by default.
  - `p95(retrieve @ 10M) < 5 ms`
  - `p95(retrieve @ 80M) < 20 ms`
  - `p99(retrieve) < 40 ms`
  - `insert_qps ≥ 200`

---

## 8. Acceptance for P4.0

P4.0 is **done** when:

1. This spec is checked into `docs/FAIM_Speed_Spec.md`.
2. `faim/speed/spec.py` encodes the same contracts as types/constants.
3. `scripts/benchmarks.py` can:
   - Load a profile (DEV, LAPTOP, SERVER),
   - Run synthetic ingest + retrieve,
   - Emit metrics that can be checked against the spec.
4. CI / local test harness has a “speed check” mode that fails if:
   - Any profile budget is exceeded on the target environment.

Later P4.x phases (VectorBank, HotCache, NVMe snapshots, write queue, GPU backend) must **prove** they meet or improve these budgets before merging into `main`. :contentReference[oaicite:18]{index=18}  
