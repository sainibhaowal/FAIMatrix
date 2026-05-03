# Phase 1 — FIG Graph API Contract (Authoritative Spec)

Date: 2026-04-04  
Status: **Implemented** — backend: `faim_native/api/routers/graph.py`, shared helpers: `faim_native/api/fig_graph_core.py`, tests: `tests/unit/test_fig_graph_mapping.py`.  
Related: `01_FigView_Explanation.md`, `02_FigView_Implementation_Plan.md`

---

## 1. What, why, where

### What

Define three **new, additive** HTTP endpoints under the existing API prefix that return a **read-only, tenant-scoped aggregate** of graph structure and explanation data for the FIG View UI:

| Method | Path                          | Role                                                                                     |
| ------ | ----------------------------- | ---------------------------------------------------------------------------------------- |
| `GET`  | `/api/v1/graph/surface`       | Initial graph load: bounded nodes, edges, snapshot, optional timeline + topology summary |
| `GET`  | `/api/v1/graph/neighborhood`  | Node-centric expansion: neighbors within hops/kinds                                      |
| `POST` | `/api/v1/graph/paths/explain` | Relation explanation: bounded path or “no path” between two nodes                        |

### Why

- **Single contract** for the visualization layer instead of N ad hoc calls (`node`, `events`, `metrics`, etc.), reducing inconsistent snapshots and race conditions in the UI.
- **Hard server-side bounds** on payload size and work (DB + CPU) for production safety.
- **Deterministic ordering** so the UI and tests are stable.
- **Additive-only**: no changes to existing router URLs, request bodies, or response shapes.

### Where (repository map)

| Area                 | Location                                                                                                                             | Role                                                                                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| API mount            | `faim_native/api/app.py`                                                                                                             | Today: `prefix = "/api/v1"`; new router will be `include_router(graph_router, prefix=prefix)` (Phase 2).                                                           |
| New router (Phase 2) | `faim_native/api/routers/graph.py`                                                                                                   | Implements this contract.                                                                                                                                          |
| Router package       | `faim_native/api/routers/__init__.py`                                                                                                | Export `graph_router`.                                                                                                                                             |
| Auth / context       | `faim_native/api/deps.py` — `get_faim_context`, `get_tenant_id`                                                                      | Same as `node`, `events`, `metrics`: tenant from middleware; repos tenant-scoped.                                                                                  |
| Models               | `faim_native/store/pg/models_faim.py` — `NodeModel`, `EdgeModel`, `EventModel`, `GraphVersionModel`                                  | Source of truth for fields; no schema change required for v1 contract.                                                                                             |
| Repos                | `faim_native/store/pg/repos/node_repo.py`, `edge_repo.py`, `event_repo.py`, `graph_version_repo.py`                                  | Listing, counts, adjacency; Phase 2 may add **private** helpers (e.g. bounded BFS) **inside** `graph.py` or repos — no change to existing public method contracts. |
| Frontend (later)     | `frontend/src/lib/figViewApi.ts`, `frontend/src/types/figView.ts`, `frontend/src/app/(app)/dashboard/graph/page.tsx`                 | Consumers of this API.                                                                                                                                             |
| Tests (Phase 3)      | `tests/acceptance/test_AT_fig_graph_api_surface.py`, `test_AT_fig_graph_tenant_isolation.py`, `tests/unit/test_fig_graph_mapping.py` | Lock the contract.                                                                                                                                                 |

---

## 2. Global rules (all three endpoints)

### 2.1 Authentication and tenancy

- **Identical** to existing v1 routes: `TenantAuthMiddleware` / `JWTAuthMiddleware` establish `request.state.tenant_id`.
- Handlers use `FAIMContext = Depends(get_faim_context)` — **no new auth mechanism**.
- **`graph_id` is required** for every call (see §2.2). Server resolves data only for `(tenant_id, graph_id)` via existing repos. **Never** trust client-supplied `tenant_id` in body for authorization.

### 2.2 `graph_id` binding

- **Query parameter**: `graph_id` (required), same style as `GET /api/v1/events?graph_id=...` and `GET /api/v1/node/{node_id}?graph_id=...`.
- **Optional header** `X-Graph-Id`: if both are present, they **must** match; if they differ → `400` with `error.code = "graph_id_mismatch"`.
- If absent → `400`, `error.code = "missing_graph_id"` (message may mirror existing “Missing graph_id” patterns).

### 2.3 Content-Type and encoding

- Request/response: `application/json; charset=utf-8`.
- All timestamps in responses: ISO 8601 UTC strings (consistent with `node` router).

### 2.4 Additive-only compatibility rule

- v1 clients **must** ignore unknown JSON keys in responses.
- Servers **may** add optional keys in minor revisions without a version bump; breaking changes require a new path (e.g. `/api/v2/graph/...`) or explicit `Accept`/version header **only if** introduced later — **out of scope for Phase 1 approval**.
- **Forbidden in v1**: removing or renaming fields documented here; changing required query/body fields; changing HTTP status semantics.

### 2.5 Request limits (hard caps)

All limits are **clamped server-side** (like `events` clamping `limit` to `MAX_PAGE_SIZE`). Clients may request lower values; higher values are reduced silently **or** rejected with `400` — pick one per endpoint below (recommended: **clamp** for UX parity with events).

| Endpoint        | Parameter        | Default | Min | Max (hard cap) |
| --------------- | ---------------- | ------- | --- | -------------- |
| `surface`       | `node_limit`     | 200     | 1   | 500            |
| `surface`       | `edge_limit`     | 800     | 0   | 2000           |
| `surface`       | `timeline_limit` | 0 (off) | 0   | 100            |
| `neighborhood`  | `depth`          | 2       | 1   | 4              |
| `neighborhood`  | `node_limit`     | 150     | 1   | 300            |
| `neighborhood`  | `edge_limit`     | 400     | 0   | 800            |
| `paths/explain` | `max_hops`       | 12      | 1   | 32             |
| `paths/explain` | `max_paths`      | 1       | 1   | 3              |

**Work budget**: If a single request would exceed caps after clamping, the server returns partial results with `truncated: true` and `truncation_reason` (see §2.8) rather than running unbounded queries.

### 2.6 Snapshot / version semantics

Each successful response includes a **`snapshot`** object:

```json
{
  "graph_id": "<string>",
  "graph_version": <int>,
  "graph_hash": "<string>",
  "as_of": "<ISO8601>",
  "consistent_read": <boolean>
}
```

| Field             | Meaning                                                                                                                                                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `graph_version`   | From `GraphVersionModel.version` / `gv_repo` for this `graph_id` (same logical meaning as elsewhere in the API).                                                                                                                                 |
| `graph_hash`      | Best-effort content fingerprint for the graph at or before this read. **May be empty string** if not computable without extra work — same degradation principle as `GET /api/v1/metrics/scorecard`.                                              |
| `as_of`           | Server UTC time when the response was assembled (for UI “stale” hints).                                                                                                                                                                          |
| `consistent_read` | `true` if all primary payloads (nodes/edges for this response) were read in **one** DB transaction or equivalent; `false` if assembled from multiple reads (UI may show a soft warning). Phase 2 should prefer a single transaction where cheap. |

**UI rule**: If the client has a cached `graph_version` / `graph_hash` and the new snapshot differs, treat prior layout positions as **hints** only and refresh structure.

### 2.7 Deterministic ordering rules

| Collection                           | Order                                                                                                     |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| `nodes[]`                            | `(created_at ascending, node_id ascending)` — aligns with `NodeRepo.list_nodes`.                          |
| `edges[]`                            | `(src_node_id ascending, dst_node_id ascending, kind ascending)` — aligns with `EdgeRepo.list_all_edges`. |
| `timeline.events[]`                  | `seq ascending` — aligns with `event_repo.get_by_seq` ordering.                                           |
| `neighborhood` nodes/edges           | Same as above **within** the returned sets.                                                               |
| `paths.explanations[]` (if multiple) | Shortest hop count first; tie-break `(lexicographic path signature of node_id sequence)`.                 |

### 2.8 Error contract

Structured body for **4xx/5xx** (where practical):

```json
{
  "error": {
    "code": "<snake_case_string>",
    "message": "<human readable>",
    "request_id": "<from middleware>",
    "details": {}
  }
}
```

| HTTP | `code`              | When                                         |
| ---- | ------------------- | -------------------------------------------- |
| 400  | `missing_graph_id`  | No `graph_id`                                |
| 400  | `graph_id_mismatch` | Query vs header conflict                     |
| 400  | `invalid_limit`     | (Optional) if rejecting instead of clamping  |
| 400  | `invalid_node_id`   | Malformed UUID                               |
| 404  | `node_not_found`    | Seed/endpoint node not in graph              |
| 422  | `validation_error`  | Pydantic body validation                     |
| 500  | `internal_error`    | Unexpected failure (no stack traces in body) |

**Logging**: Use existing request-id middleware; **do not** log full payloads or secrets.

---

## 3. Endpoint: `GET /api/v1/graph/surface`

### 3.1 Purpose

**Graph load**: return a **bounded** set of nodes and edges plus optional **timeline** and **topology summary** for the inspector. This is the FIG entry payload.

### 3.2 Query parameters

| Name               | Type   | Default | Description                                                                               |
| ------------------ | ------ | ------- | ----------------------------------------------------------------------------------------- |
| `graph_id`         | string | —       | Required.                                                                                 |
| `node_limit`       | int    | 200     | Clamped 1–500.                                                                            |
| `edge_limit`       | int    | 800     | Clamped 0–2000.                                                                           |
| `timeline_limit`   | int    | 0       | If `> 0`, include recent events (clamped 1–100). `0` = omit timeline block entirely.      |
| `after_seq`        | int    | 0       | Only if `timeline_limit > 0`; same semantics as `GET /api/v1/events` (`seq > after_seq`). |
| `include_topology` | bool   | `true`  | If `false`, omit `topology` object (save CPU).                                            |

### 3.3 Response shape (200)

Top-level keys (order not normative):

```json
{
  "snapshot": {},
  "nodes": [],
  "edges": [],
  "timeline": null,
  "topology": null,
  "controls": {},
  "truncated": false,
  "truncation_reason": null
}
```

#### 3.3.1 `nodes[]` — `GraphNode`

| Field         | Type   | Required | Notes                                                                             |
| ------------- | ------ | -------- | --------------------------------------------------------------------------------- |
| `node_id`     | string | yes      | UUID string                                                                       |
| `kind`        | string | yes      | e.g. `atom`, `macro`                                                              |
| `level`       | int    | yes      |                                                                                   |
| `vector_hash` | string | yes      |                                                                                   |
| `display`     | object | yes      | See §5 (title fallback + display state)                                           |
| `metrics`     | object | no       | Optional UI metrics: `touch_count`, `residual` (float), `last_access` ISO or null |
| `provenance`  | object | no       | Safe subset: `raw_id`, `block_id` if present (no `v_native` / full vectors in v1) |

#### 3.3.2 `edges[]` — `GraphEdge`

| Field         | Type           | Required |
| ------------- | -------------- | -------- | --------------------------------------------------------- |
| `edge_id`     | string         | yes      |
| `src_node_id` | string         | yes      |
| `dst_node_id` | string         | yes      |
| `kind`        | string         | yes      |
| `weight`      | float          | yes      | Normalized like existing APIs (`/ 1e9`)                   |
| `meta`        | object or null | yes      | Pass-through from `EdgeModel.meta` when JSON-serializable |

#### 3.3.3 `timeline` (optional)

If `timeline_limit > 0`:

```json
{
  "after_seq": 0,
  "next_seq": 123,
  "has_more": false,
  "events": [
    {
      "seq": 1,
      "kind": "<string>",
      "ts": "<ISO8601>",
      "payload_keys": ["..."],
      "graph_id": "<string>"
    }
  ]
}
```

**Semantics** (timeline window):

- **Window**: Events with `seq > after_seq`, ordered by `seq` ascending, at most `timeline_limit` rows.
- **Payload**: **Same privacy posture as** `GET /api/v1/node/{id}/explain` recent events: **do not** echo full `payload` by default — only `payload_keys` unless a future flag explicitly allows redacted payload (out of v1).
- **Consistency**: Timeline may be from the same transaction as nodes/edges or not; if not, set `snapshot.consistent_read` to `false`.

#### 3.3.4 `topology` (optional)

If `include_topology` is true:

```json
{
  "node_count": 0,
  "edge_count": 0,
  "edge_counts_by_kind": { "inheritance": 0, "opposition": 0 },
  "scorecard": null
}
```

| Field                       | Policy                                                                                                                                                                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `node_count` / `edge_count` | From repo `count()` for this graph — **O(1) or cheap aggregate**, acceptable.                                                                                                                                                              |
| `edge_counts_by_kind`       | **Best-effort**; if expensive in Phase 2, may omit keys or set `{}` and `truncated` false.                                                                                                                                                 |
| `scorecard`                 | Optional embedded subset of **existing** `MetricsScorecard`-style fields (D, H, λ, redundancy, etc.) **only** if already available via shared helper with `metrics` router — **no duplicate business logic** and **no fabricated values**. |

#### 3.3.5 `controls` — similarity and filters (declaration, not mutation)

```json
{
  "similarity": {
    "mode": "none",
    "notes": "Exploration filters affect ranking only; they do not mutate graph truth."
  }
}
```

v1 **does not** apply similarity on `surface` unless Phase 2 implements an optional query param (see §6). Until then, `mode` is always `none` and `notes` is static.

### 3.4 Validation checklist (surface)

- [x] Request limits defined (§2.5, §3.2).
- [x] Response shape defined (§3.3).
- [x] Snapshot semantics (§2.6).
- [x] Deterministic ordering (§2.7).
- [x] Timeline window semantics (§3.3.3).
- [x] Similarity placeholder (§3.3.5, §6).
- [x] Display state + title strategy (§5).
- [x] Topology policy (§3.3.4).
- [x] Deep links (§7).

---

## 4. Endpoint: `GET /api/v1/graph/neighborhood`

### 4.1 Purpose

**Node expansion**: from a **seed** `node_id`, return nodes and edges within `depth` hops over **allowed edge kinds**.

### 4.2 Query parameters

| Name         | Type   | Default                  | Description                                       |
| ------------ | ------ | ------------------------ | ------------------------------------------------- |
| `graph_id`   | string | —                        | Required.                                         |
| `node_id`    | string | —                        | Required. Seed node UUID.                         |
| `depth`      | int    | 2                        | Clamped 1–4.                                      |
| `node_limit` | int    | 150                      | Clamped 1–300.                                    |
| `edge_limit` | int    | 400                      | Clamped 0–800.                                    |
| `edge_kinds` | string | `inheritance,opposition` | Comma-separated allowlist; unknown kinds ignored. |

### 4.3 Response shape (200)

```json
{
  "snapshot": {},
  "seed_node_id": "<uuid>",
  "depth_requested": 2,
  "depth_effective": 2,
  "nodes": [],
  "edges": [],
  "distances": {},
  "truncated": false,
  "truncation_reason": null
}
```

#### 4.3.1 `distances` — relation-distance field policy

| Key           | Value                                                                                                                    |
| ------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Format        | `Record<node_id, int>`                                                                                                   |
| Meaning       | **Graph hop distance** from `seed_node_id` along **allowed** edges only, unweighted.                                     |
| Missing nodes | Only nodes present in `nodes[]` need entries; seed has `0`.                                                              |
| Overflow      | If truncated before full frontier, omit distance for unreached nodes or cap at `depth_effective` with `truncated: true`. |

**Policy**: Distances are **structural** (topology), not embedding similarity. Similarity remains a separate control (§6).

### 4.4 Errors

- `404` + `node_not_found` if seed not in graph.

---

## 5. Node title fallback and display-state mapping

### 5.1 `display.title` and `display.title_source`

Server computes **read-only** display strings; the UI must not invent titles that imply false provenance.

**Fallback order** (first non-empty wins):

1. **Anchor text** — if `anchor_json` has a documented safe key (Phase 2 picks **one** stable key, e.g. `title` or `label` if present and non-empty string).
2. **`block_id`** (truncated to max 64 chars).
3. **`raw_id`** prefix (truncated).
4. **`kind` + short `vector_hash` prefix** (e.g. first 8 hex chars).
5. **`node_id` prefix** (last resort).

`title_source` is one of: `anchor`, `block_id`, `raw_id`, `vector_hash`, `node_id`, `unknown`.

### 5.2 `display.state` — taxonomy

Closed set for v1:

`active` | `historical` | `compressed` | `deduplicated` | `pruned` | `cold` | `deactivated` | `unknown`

**Mapping policy** (conservative):

| State                                                                   | When (initial rules; Phase 2 implements only when evidence exists)                                                             |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `unknown`                                                               | Default when no reliable signal                                                                                                |
| `cold`                                                                  | `last_access` older than threshold **or** `touch_count == 0` with age > T (T configurable server-side constant)                |
| `active`                                                                | Recently accessed or high `touch_count`                                                                                        |
| `pruned` / `deduplicated` / `compressed` / `deactivated` / `historical` | Set **only** when derived from **explicit** event kinds or node/edge metadata documented in evolve/storage — **never guessed** |

If ambiguous → `unknown`. The UI renders `unknown` neutrally.

---

## 6. Similarity-control semantics

- **v1 principle**: Similarity controls are **exploration filters** — they change **ranking/subsetting** of what the FIG shows, **not** graph truth on the server.
- **surface/neighborhood optional future query** (not required for contract approval): `similarity_mode=none|neighbor_embedding` with strict caps. If unsupported, server returns success with `controls.similarity.mode = "none"`.
- **No writing** vectors or edges via these endpoints.

---

## 7. Safe deep-link policy

Returned **only** when safe and tenant-consistent:

| Target          | Condition                                                                                                                                                                                                                    |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Storage file    | `provenance.raw_id` present **and** storage catalog has a file for `(tenant, graph_id, raw_id)` — link template documented in frontend as `/dashboard/storage` with existing query conventions **without** exposing secrets. |
| Node detail API | `GET /api/v1/node/{node_id}?graph_id=...` (same origin)                                                                                                                                                                      |
| Evolution page  | Generic `/dashboard/evolution` only — **no** internal job ids in URL unless already a public pattern elsewhere                                                                                                               |

**Forbidden**: embedding API keys, full `v_native`, or cross-tenant identifiers in links.

---

## 8. Endpoint: `POST /api/v1/graph/paths/explain`

### 8.1 Purpose

**Relation explanation**: given `from_node_id` and `to_node_id`, return whether a path exists within constraints, and a **bounded** explanation suitable for the inspector (not a full graph export).

### 8.2 Request body

```json
{
  "from_node_id": "<uuid>",
  "to_node_id": "<uuid>",
  "max_hops": 12,
  "max_paths": 1,
  "edge_kinds": ["inheritance", "opposition"]
}
```

| Field          | Required | Notes                                   |
| -------------- | -------- | --------------------------------------- |
| `from_node_id` | yes      | UUID string                             |
| `to_node_id`   | yes      | UUID string                             |
| `max_hops`     | no       | Default 12; clamped 1–32                |
| `max_paths`    | no       | Default 1; clamped 1–3                  |
| `edge_kinds`   | no       | Default `["inheritance", "opposition"]` |

`graph_id` comes from **query** (same as GET endpoints), not from body, to match the rest of the API.

### 8.3 Response shape (200)

Always **200** for well-formed requests (UI avoids treating “no path” as 404):

```json
{
  "snapshot": {},
  "from_node_id": "<uuid>",
  "to_node_id": "<uuid>",
  "path_found": false,
  "paths": [],
  "explanation": {
    "summary": "<string>",
    "hops": 0,
    "edge_kinds_used": [],
    "relation_distance": null
  }
}
```

When `path_found` is true:

- `paths[]` contains up to `max_paths` items, each:

```json
{
  "node_ids": ["..."],
  "edges": [
    {
      "edge_id": "",
      "src_node_id": "",
      "dst_node_id": "",
      "kind": "",
      "weight": 0.0
    }
  ]
}
```

- `explanation.relation_distance` = hop count of **shortest** returned path.
- `explanation.summary` = short deterministic template, e.g. `"inheritance path, 3 hops"` (no LLM).

### 8.4 Errors

- `404` if `from_node_id` or `to_node_id` not found in graph (optional: split into `partial_node_missing` in `details`).

---

## 9. What must not break

| Surface                             | Constraint                                                                                           |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Storage API**                     | No changes to URLs, models, or `storage_contract` validations in `app.py` startup.                   |
| **Memory API**                      | No change to write paths, idempotency, or response contracts.                                        |
| **Evolution API**                   | No change to evolve job contracts or scheduler behavior.                                             |
| **Events / SSE**                    | No change to stream semantics; graph timeline is a **subset view**, not a replacement.               |
| **Query / Node / Metrics / Ingest** | Unchanged; graph router **reads** same stores only.                                                  |
| **Auth / crypto**                   | No new secrets; no weaker tenant checks.                                                             |
| **Frontend**                        | Existing pages (`storage`, `evolution`, shell) keep current API usage until FIG explicitly migrates. |

---

## 10. Phase 2 implementation notes (non-normative)

- Implement `APIRouter(prefix="/graph", tags=["graph"])` so full paths match this doc under `/api/v1`.
- Reuse `NodeRepo.list_nodes` / `list_all_edges` patterns for ordering; for neighborhood and paths, implement **bounded** graph algorithms with early exit when `node_limit` or `edge_limit` hit.
- Do not expose raw embedding vectors in v1.
- After implementation: run full pytest + listed acceptance tests in `02_FigView_Implementation_Plan.md` §Phase 3.

---

## 11. Validation vs goals

| Goal                                        | §          |
| ------------------------------------------- | ---------- |
| Contract covers graph load                  | §3         |
| Contract covers node expansion              | §4         |
| Contract covers relation explanation        | §8         |
| Does not break Storage / Memory / Evolution | §9         |
| Request limits                              | §2.5       |
| Response shapes                             | §3–§8      |
| Snapshot/version semantics                  | §2.6       |
| Deterministic ordering                      | §2.7       |
| Error contract                              | §2.8       |
| Additive-only rule                          | §2.4       |
| Timeline window                             | §3.3.3     |
| Similarity semantics                        | §3.3.5, §6 |
| Title fallback                              | §5.1       |
| Display state                               | §5.2       |
| Relation distance                           | §4.3.1     |
| Topology summary                            | §3.3.4     |
| Deep links                                  | §7         |

---

## 12. Acceptance gate

- [ ] Stakeholder sign-off on caps (`node_limit` / `edge_limit` / `depth` / `max_hops`).
- [ ] Sign-off on **timeline payload** (`payload_keys` only vs richer redacted payload later).
- [ ] Sign-off on **display.state** mapping when evolve/event evidence is incomplete (default `unknown`).
- [ ] **Explicit approval** recorded before merging `faim_native/api/routers/graph.py`.

---

_End of Phase 1 contract document._
