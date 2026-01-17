# Stage-7 Report: API + SSE Alive Event Stream + Tenant Auth

## ✅ Test Results

```
======================= 313 passed, 2 warnings in 1.59s ========================
```

---

## Summary

Stage-7 exposes the FAIM engine through a production-ready FastAPI surface:

- Multi-tenant isolation (hard separation)
- SSE "Alive" event stream for UI
- Deterministic + replay-safe (events = truth trace)

---

## Files Delivered

### Schema Changes

| Model             | Column Added             |
| ----------------- | ------------------------ |
| EventModel        | `tenant_id` (default="") |
| NodeModel         | `tenant_id` (default="") |
| EdgeModel         | `tenant_id` (default="") |
| SnapshotModel     | `tenant_id` (default="") |
| GraphVersionModel | `tenant_id` (default="") |

### Middleware

| File                           | Description                        |
| ------------------------------ | ---------------------------------- |
| `api/middleware/auth.py`       | X-Tenant-Id + X-Api-Key validation |
| `api/middleware/request_id.py` | Correlation ID                     |

### Routers (8)

| File         | Endpoints                 |
| ------------ | ------------------------- |
| `health.py`  | GET /health, /version     |
| `ingest.py`  | POST /v1/ingest           |
| `query.py`   | POST /v1/query            |
| `node.py`    | GET /v1/node/{id}         |
| `events.py`  | SSE stream + pagination   |
| `evolve.py`  | POST /v1/evolve           |
| `metrics.py` | GET /v1/metrics/scorecard |
| `admin.py`   | Protected admin endpoints |

### Other Files

| File                 | Description  |
| -------------------- | ------------ |
| `api/app.py`         | FastAPI app  |
| `api/deps.py`        | Dependencies |
| `runtime/context.py` | Repo wiring  |

---

## Acceptance Tests (7)

| Test                                    | Gate                 |
| --------------------------------------- | -------------------- |
| `test_AT_A1_tenant_auth_required`       | No headers → 401     |
| `test_AT_A2_tenant_isolation_events`    | Tenant isolation     |
| `test_AT_A3_ingest_emits_events`        | Events emitted       |
| `test_AT_A4_sse_resume_after_seq`       | SSE resume           |
| `test_AT_A5_query_deterministic_strict` | STRICT determinism   |
| `test_AT_A6_node_inspector_no_leak`     | No cross-tenant leak |
| `test_AT_A7_evolve_lock_single_writer`  | Lock works           |

---

## API Endpoints

| Method | Path                  | Auth         |
| ------ | --------------------- | ------------ |
| GET    | /health               | None         |
| GET    | /version              | None         |
| POST   | /v1/ingest            | Tenant       |
| POST   | /v1/query             | Tenant       |
| GET    | /v1/node/{id}         | Tenant       |
| GET    | /v1/events            | Tenant       |
| GET    | /v1/events/stream     | Tenant (SSE) |
| GET    | /v1/events/latest     | Tenant       |
| POST   | /v1/evolve            | Tenant       |
| GET    | /v1/metrics/scorecard | Tenant       |
| POST   | /v1/admin/\*          | Admin        |

---

## Usage

```bash
# Start API
cd /home/sephi-asi/FAIM/faim/Faim_Native
uvicorn api.app:app --reload

# With tenant auth
curl -H "X-Tenant-Id: demo" -H "X-Api-Key: key" \
  http://localhost:8000/v1/events?graph_id=my_graph
```
