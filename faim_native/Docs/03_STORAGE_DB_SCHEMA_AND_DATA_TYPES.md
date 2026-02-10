# 03 - Storage DB Schema and Data Types

This document explains where FAIM data is stored and in what representation.

## 1) Storage Layers by Responsibility

## Postgres (truth)

Holds durable metadata and graph state:

- `raw_refs`
- `nodes`
- `edges`
- `events`
- `graph_version`
- `snapshots`
- `ingest_dedup`
- `jobs` and `job_events`
- auth tables (`tenant_api_keys`, `admin_api_keys`, `users`)

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

## `nodes`

- atom/macro memory nodes
- important columns: `node_id`, `tenant_id`, `graph_id`, `kind`, `vector_hash`, `raw_id`, `block_id`, `anchor_json`, `v_native`, `opp_signature`, `residual`, `level`, `touch_count`

## `edges`

- relationship graph
- `kind` in practice: inheritance/opposition
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

## 3) Data Representation Types

| Domain Data | Runtime Type | Storage Type |
|---|---|---|
| Raw uploaded file | `bytes` | Filesystem blob + `raw_refs` metadata |
| Extracted block text | `str` | transient (may be persisted indirectly via node evidence fields) |
| Anchor metadata | dict/typed object | `anchor_json` (`JSONB`) |
| Vector (`v_native`) | tuple/list of 256 `float` | `nodes.v_native` (`JSONB`) |
| Opposition signature | dict of floats | `nodes.opp_signature` (`JSONB`) |
| Packet hash / vector hash / checksums | hex string | `VARCHAR/TEXT` |
| Edge weights | float in code | scaled integer in DB (`BigInteger` with `*1e9`) |
| Residual | float in code | scaled integer in DB (`BigInteger` with `*1e9`) |
| Event payload | dict | `JSONB` |

## 4) Numeric and Matrix Semantics

FAIM stores memory in mixed symbolic + numeric form:

- Symbolic: block content, anchors, event payloads, IDs, hashes.
- Numeric vectors: 256-dim float vectors (`v_native`).
- Graph math primitives: cosine similarity, weighted parent fractions, residual novelty, opposition score.

This is effectively:

- text/evidence atoms
- vector space representation (dense numeric arrays)
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
- `raw_refs` table exists and is robust, but ingest API wiring to it must be completed.
