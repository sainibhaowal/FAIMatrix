# Stage-6 Report: Index/Cache FAIM-Native

## ✅ Test Results

```
=========== 273 passed, 1 warning in 1.45s ============
```

---

## Summary

Stage-6 makes `index/` and `cache/` **acceleration-only** layers that are:

- Deterministic in STRICT mode (no index writes)
- Never a second truth system (can be deleted and rebuilt)
- Gracefully degrade when external services unavailable

---

## Non-Negotiables Verified

| Rule                                       | Status |
| ------------------------------------------ | ------ |
| Index dim = 256 from encoding schema       | ✅     |
| Point IDs deterministic (no Python hash()) | ✅     |
| Fallback when Qdrant/Redis down            | ✅     |
| Cache keys include graph_version           | ✅     |
| STRICT mode skips index writes             | ✅     |

---

## Deliverables

### A) Index (Qdrant) — REWRITTEN ✅

| File                    | What It Does                                            |
| ----------------------- | ------------------------------------------------------- |
| `index/collections.py`  | Schema: faim\_<tenant>, dim=256, cosine, payload fields |
| `index/qdrant_index.py` | FAIMIndex + BruteForceIndex fallback, stable sort       |

**Key Changes**:

- Dimension: 256 (imported from `encoding.vector_schema.VECTOR_DIMENSION`)
- Point IDs: Use node_id directly (not Python `hash()`)
- Fallback: In-memory brute-force when Qdrant unavailable
- Sorting: Results sorted by `(-score, node_id)` for stable ties

---

### B) Cache (Redis) — CREATED ✅

| File                   | What It Does                                    |
| ---------------------- | ----------------------------------------------- |
| `cache/query_cache.py` | QueryCache + StatsCache with version-aware keys |
| `cache/locks.py`       | RedisLock + FileLock + LockManager              |

**Key Format**:

```
faim:query:<tenant>:<graph>:v<version>:<query_hash>:<profile>:k<k>
```

**Guarantees**:

- Version change → old cache key is different → stale not returned
- Redis down → returns None (no crash)
- Locks: Redis `SET NX PX` with file fallback

---

### C) Orchestration Wiring ✅

| File             | Changes                                                     |
| ---------------- | ----------------------------------------------------------- |
| `ingest_flow.py` | +50 lines: Index upsert after write_atoms (STRICT disabled) |
| `evolve_flow.py` | +25 lines: Wrapped in evolve_lock context manager           |

---

## New Tests (23)

| Test File                     | Tests |
| ----------------------------- | ----- |
| `test_index_faim_native.py`   | 8     |
| `test_cache_faim_native.py`   | 10    |
| `test_orchestration_index.py` | 5     |

---

## Usage Examples

```python
# Index with fallback
from index.qdrant_index import FAIMIndex
index = FAIMIndex(project_id)  # dim=256 enforced
index.add(graph_id, node_id, vector)  # Deterministic point_id

# Cache with version
from cache.query_cache import QueryCache
cache = QueryCache(tenant_id)
results = cache.get(graph_id, graph_version=42, ...)  # Version in key!

# Lock for evolution
from cache.locks import evolve_lock
with evolve_lock(graph_id) as acquired:
    if acquired:
        # Protected code
```

---

## Definition of Done

| Criterion                                     | Status   |
| --------------------------------------------- | -------- |
| All tests pass                                | ✅ (273) |
| No numpy/sentence-transformers in index/cache | ✅       |
| Index+cache deletable without truth loss      | ✅       |
| STRICT is deterministic                       | ✅       |
