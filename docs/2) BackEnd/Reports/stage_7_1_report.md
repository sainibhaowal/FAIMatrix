# Stage-7.1 Report: Production Hardening

## ✅ Test Results

```
======================= 332 passed, 2 warnings in 1.62s ========================
✓ All tests passed!
```

---

## Changes Made

### 1. Schema (schema.sql)

- Added `tenant_id TEXT NOT NULL` to all 6 tables
- Added composite indexes:
  - `events(tenant_id, graph_id, seq)`
  - `nodes(tenant_id, graph_id)` + `UNIQUE(tenant_id, graph_id, vector_hash)`
  - `edges(tenant_id, graph_id)`
  - `snapshots(tenant_id, graph_id, created_at DESC)`
  - `graph_version(tenant_id, graph_id)` as PK
- Added `reject_empty_tenant()` trigger on all tables

### 2. ORM Models

- Removed `default=""` from all tenant_id columns
- Added `tenant_id` param to all `from_domain()` methods with `__test__` default

### 3. Repos

- `NodeRepo.__init__(session, tenant_id="__test__")`
- `EdgeRepo.__init__(session, tenant_id="__test__")`
- `GraphVersionRepo.bump(..., tenant_id="__test__")`
- `GraphVersionRepo.set_version(..., tenant_id="__test__")`

### 4. Auth Middleware

- `normalize_tenant_id()` with pattern validation
- `_constant_time_compare()` using `hmac.compare_digest`
- Key rotation: `["key1", "key2"]` per tenant

### 5. SSE Generator

- Uses `_get_fresh_session()` per fetch
- `MAX_PAGE_SIZE = 100`
- `HEARTBEAT_INTERVAL_SECONDS = 15.0`
- `MAX_EMPTY_POLLS = 300` (5 min timeout)
- Clean `CancelledError` handling

---

## New Tests (19)

| Test Class           | Tests |
| -------------------- | ----- |
| TestTenantIdRequired | 6     |
| TestAuthHardening    | 5     |
| TestSSEHardening     | 5     |
| TestSchemaIndexes    | 3     |
