# 03 - Storage DB Schema and Data Model Report

Date: 2026-02-11
Owner: FAIM Native Runtime
Status: Completed

## Objective

Document the implemented Postgres, Redis, Qdrant, and raw-store schema/data representation used by FAIM Native.

This document explains where FAIM data is stored and in what representation.

## 1) Storage Layers by Responsibility

## Postgres (truth)

Holds durable metadata and graph state:

- `raw_refs`
- `storage_files`
- `nodes`
- `node_repr_v2`
- `graph_repr_v2_stats`
- `graph_term_stats`
- `graph_canonical_lexicon`
- `edges`
- `events`
- `graph_version`
- `snapshots`
- `ingest_dedup`
- `jobs` and `job_events`
- `self_invention_state`
- `tenant_crypto_keys`
- auth tables (`tenant_api_keys`, `auth_key_audit_log`, `users`)

## Filesystem Raw Store (truth for raw bytes)

Immutable content-addressed blobs:

- path pattern: `{base}/{sha256[:2]}/{sha256}`
- raw bytes are stored once per hash

## Redis (acceleration/coordination)

- query cache keys
- stats cache keys
- auth OTP/rate-limit state
- lock support and rate limiting

## Qdrant (acceleration only)

- vector index copies for fast nearest-neighbor retrieval
- never source of truth

## 2) Core Postgres Tables and Semantics

## `raw_refs`

- stores immutable raw blob metadata
- important columns: `id`, `tenant_id`, `sha256`, `uri`, `mime_type`, `size_bytes`, `graph_id`

## `storage_files`

- storage catalog/lifecycle table used by Storage UI/API
- important columns: `raw_id`, `tenant_id`, `graph_id`, `filename`, `mime_type`, `size_bytes`, `sha256`, `ingest_status`, `packet_hash`, `node_count`, `vector_count`, `delete_requested`

## `nodes`

- atom/macro memory nodes
- important columns: `node_id`, `tenant_id`, `graph_id`, `kind`, `vector_hash`, `raw_id`, `block_id`, `anchor_json`, `v_native`, `opp_signature`, `residual`, `level`, `touch_count`

## `node_repr_v2`

- additive lexical-semantic sidecar keyed by `node_id`
- important columns: `tenant_id`, `graph_id`, `repr_hash`, `word_counts`, `phrase_counts`, `skip_counts`, `entity_tokens`, `time_tokens`, `layout_tokens`, `channel_lengths`

## `graph_repr_v2_stats`

- graph-scoped BM25/document-frequency stats for Representation V2
- important columns: `tenant_id`, `graph_id`, `channel`, `doc_count`, `avg_len`, `df_map`
- existing graphs can rebuild these sidecars through `POST /api/v1/storage/graphs/{graph_id}/representation-v2/rebuild`

## `graph_term_stats`

- graph-scoped canonical term and phrase statistics for deterministic corpus mining
- important columns: `tenant_id`, `graph_id`, `channel`, `term`, `df`, `cf`, `doc_count`, `context_terms`

## `graph_canonical_lexicon`

- graph-scoped canonical lexical mappings mined from aliases, acronym patterns, phrase templates, and corpus statistics
- important columns: `tenant_id`, `graph_id`, `surface_form`, `canonical_form`, `kind`, `support_count`, `score`, `meta`
- existing graphs can rebuild these artifacts through `POST /api/v1/storage/graphs/{graph_id}/canonical-semantics/rebuild`

## `edges`

- relationship graph
- `kind` in practice: inheritance/opposition plus semantic kinds including `synonym`, `hypernym`, `hyponym`, `related`, `distributional_synonym`, `paraphrase`
- `weight` stores fraction/magnitude

## `events`

- append-only event journal with strict `seq`
- integrity checksum stored per event

## `graph_version`

- monotonic versioning for invalidation and replay consistency

## `snapshots`

- snapshot metadata and graph hash receipts

## `ingest_dedup`

- dedup key: `(tenant_id, graph_id, packet_hash)`
- tracks successful ingest packet hashes

## `tenant_crypto_keys`

- tenant key-wrapping metadata for envelope encryption-at-rest workflow
- important columns: `tenant_id`, `dek_wrapped`, `created_at`, `rotated_at` (when rotated)

## `tenant_api_keys`

- hashed tenant API keys (Argon2id hash, no plaintext storage)
- important columns:
  - identity: `tenant_id`, `key_id`, `key_prefix`, `key_hash`
  - authz/lifecycle: `scopes`, `expires_at`, `revoked_at`, `revoked_reason`
  - operations: `created_by`, `rotated_from_key_id`, `last_used_at`, `created_at`

## `auth_key_audit_log`

- append-only key lifecycle audit stream
- important columns: `tenant_id`, `key_id`, `action`, `actor`, `request_id`, `meta`, `created_at`

## `self_invention_state`

- incremental cursor + bounded coactivation counters for self-inventing runtime
- important columns: `tenant_id`, `graph_id`, `last_event_seq`, `signature_counts`, `last_cycle_macros`, `last_cycle_at`

## 3) Data Representation Types

| Domain Data | Runtime Type | Storage Type |
|---|---|---|
| Raw uploaded file | `bytes` | Filesystem blob + `raw_refs` metadata |
| Extracted block text | `str` | transient (may be persisted indirectly via node evidence fields) |
| Anchor metadata | dict/typed object | `anchor_json` (`JSONB`) |
| Vector (`v_native`) | tuple/list of 256 `float` | `nodes.v_native` (`JSONB`) |
| Representation V2 sparse channels | dict/list sidecar | `node_repr_v2.*` (`JSONB`) |
| Representation V2 graph stats | dict + numeric sidecar | `graph_repr_v2_stats.*` |
| Canonical term stats | dict + numeric sidecar | `graph_term_stats.*` |
| Canonical lexicon | dict + numeric sidecar | `graph_canonical_lexicon.*` |
| Domain lexicon | dict + numeric sidecar | `graph_domain_lexicon.*` |
| KB source registry | dict sidecar | `graph_kb_sources.*` |
| Opposition signature | dict of floats | `nodes.opp_signature` (`JSONB`) |
| Packet hash / vector hash / checksums | hex string | `VARCHAR/TEXT` |
| Edge weights | float in code | scaled integer in DB (`BigInteger` with `*1e9`) |
| Residual | float in code | scaled integer in DB (`BigInteger` with `*1e9`) |
| Event payload | dict | `JSONB` |
| Tenant DEK wrapped key | base64/text blob | `tenant_crypto_keys.dek_wrapped` |
| API key scopes | list of strings | `tenant_api_keys.scopes` (`JSONB`) |

## 4) Numeric and Matrix Semantics

FAIM stores memory in mixed symbolic + numeric form:

- Symbolic: block content, anchors, event payloads, IDs, hashes.
- Numeric vectors: 256-dim float vectors (`v_native`).
- Sparse lexical-semantic sidecars: hashed word/phrase/skip channels plus entity/time/layout tokens.
- Canonical semantics sidecars: graph-local term statistics and lexical mappings for query-time canonicalization.
- Graph math primitives: cosine similarity, weighted parent fractions, residual novelty, opposition score.

This is effectively:

- text/evidence atoms
- vector space representation (dense numeric arrays)
- sparse lexical-semantic representation (Representation V2 sidecars)
- canonical lexical-semantic statistics and mappings (Phase 2 sidecars)
- graph structure (nodes/edges)

## 5) Redis Key Shapes (current modules)

Examples:

- `faim:query:<tenant>:<graph>:v<version>:<query_hash>:<profile>:k<k>`
- `faim:stats:<tenant>:<graph>:v<version>`
- `faim:lock:<key>`
- auth state keys under `auth:*` namespace

## 6) Qdrant Payload Schema

Per point payload includes:

- `graph_id`
- `node_id`
- `level`
- `kind`

Collection dimension is fixed to 256.

## 7) Observed Schema/Contract Notes

- `residual` and `edge.weight` are scaled integer storage in ORM models.
- `ingest_dedup.raw_id` uses UUID type, while ingest surface often treats raw_id as plain string.
- ingest/storage API paths are wired to persist immutable raw bytes and `raw_refs` metadata before orchestration.
