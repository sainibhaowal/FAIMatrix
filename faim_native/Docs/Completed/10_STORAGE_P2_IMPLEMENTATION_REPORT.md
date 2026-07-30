# 10 - Storage P2 Implementation Report (Security/Performance Hardening)

Date: 2026-02-10
Owner: FAIM Native Runtime
Status: Completed

Scope implemented:

1. encryption-at-rest integration
2. query cache/index integration hardening
3. perf layer evaluation decision and isolation marker

## 1) Encryption-at-Rest Integration

## What changed

- `faim_native/runtime/context.py`
  - raw store construction is now env-gated for encryption-at-rest.
  - supports `FAIM_PAYLOAD_CIPHER=envelope` directly.
  - if `FAIM_ENCRYPTION_AT_REST=true` and cipher mode is unset, defaults to `envelope`.
  - supports fail-closed mode via `FAIM_ENCRYPTION_FAIL_CLOSED=true`.
  - raw store is resolved per tenant when encryption mode is active.

- `faim_native/store/crypto/envelope.py`
  - added `TenantDEKManager` for tenant DEK lifecycle.
  - DEKs are generated per tenant, wrapped by master key, and persisted in DB.
  - added runtime helpers `encryption_at_rest_enabled()` and `encryption_fail_closed()`.

- `faim_native/store/raw/crypto.py`
  - added `EnvelopeCipher`.
  - `build_cipher_from_env(...)` now supports `envelope` mode and explicit mode override.

- `faim_native/store/raw/encrypted_payload_store.py`
  - now supports method parity used by API/health paths:
    - `get_stats()`
    - `exists_by_sha(...)`
    - `load_by_sha(...)`
    - `verify(...)`
  - supports optional graph scope override on store/load calls.

- `faim_native/store/pg/models_crypto.py`
  - tenant key model timestamps normalized to timezone-aware UTC defaults.

- DB and migration wiring
  - `faim_native/store/pg/schema.sql`: `tenant_crypto_keys` table + index/comments.
  - `faim_native/store/pg/migrations/0006_tenant_crypto_keys.sql`: additive migration.
- `faim_native/store/pg/models_faim.py`: `create_all_tables()` now imports crypto models to ensure table creation.
- `faim_native/api/routers/health.py`: readiness required tables includes `tenant_crypto_keys`.

Historical plaintext blob migration support is implemented separately in
`faim_native/orchestration/jobs/raw_reencryption.py` and exposed through the
storage router execute/job endpoints plus maintenance-history visibility.

## Security model in runtime path

- raw upload bytes are encrypted before filesystem persistence when envelope mode is enabled.
- per-tenant DEK is used; wrapped DEK is persisted in Postgres.
- encrypted payload uses AES-256-GCM envelope blob format.
- hash verification still occurs on stored ciphertext blobs before decryption.

## 2) Cache + Index Integration Hardening

## What changed

- `faim_native/orchestration/query_flow.py`
  - `run_query(..., cache=None)` now supports cache integration.
  - graph version resolved with tenant-aware `GraphVersionRepo(tenant_id=...)`.
  - recall candidates attempt cache read first.
  - on miss, candidates are computed and cached.
  - adds `metrics.cache_hit` indicator.

- `faim_native/api/routers/query.py`
  - passes `ctx.cache` into query flow.
  - `QueryMetrics` includes `cache_hit`.

- `faim_native/cache/query_cache.py`
  - `QueryCache`/`StatsCache` now accept both `UUID` and `str` tenant IDs.

- `faim_native/core/query/query_engine.py`
  - `recall_candidates_index(...)` now supports both:
    - preferred `top_k(...)`
    - legacy `search(...)`
  - invalid IDs are ignored safely.
  - stable sort maintained (`-score`, `node_id`).

- `faim_native/index/qdrant_index.py`
  - added legacy-compatible `search(...)` wrapper that maps to `top_k(...)`.

- `faim_native/orchestration/ingest_flow.py`
  - index upsert now uses canonical `write_result.node_ids`, improving query/index alignment.

## 3) Perf Layer Evaluation

Decision: **isolate** current perf namespace from active ingest/query production path.

- Added `faim_native/orchestration/perf/__init__.py` with:
  - `PERF_LAYER_STATUS = "isolated_legacy"`

Rationale:

- avoids accidental production coupling to legacy/namespace-misaligned modules
- keeps current P0/P1/P2 storage path stable while preserving future integration option

## 4) Tests Added (P2)

- `tests/unit/test_p2_encryption_at_rest.py`
  - tenant DEK manager roundtrip
  - encrypted raw store ciphertext-at-rest behavior

- `tests/unit/test_p2_query_cache_index_alignment.py`
  - index contract alignment (`top_k` and legacy `search`)
  - query flow cache wiring assertions

- `tests/acceptance/test_AT_P2_security_perf_surface.py`
  - migration presence check
  - query flow cache parameter contract
  - perf layer isolation marker check

## 5) Operational Notes

- Encryption mode is opt-in via environment flags.
- `FAIM_ENCRYPTION_FAIL_CLOSED=true` is recommended for production.
- Existing plaintext raw blobs are not reencrypted automatically during normal ingest.
  - they can now be migrated explicitly with the guarded raw-reencryption endpoint/job.
