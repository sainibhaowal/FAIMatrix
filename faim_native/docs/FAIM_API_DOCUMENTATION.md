# FAIM-Native API Documentation

> **Version:** 0.10.0  
> **Base URL:** `http://localhost:8000`  
> **Authentication:** JWT (Bearer) or API Key (X-Api-Key + X-Tenant-Id)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
   - [Health](#health-endpoints)
   - [Auth](#auth-endpoints)
   - [Query](#query-endpoints)
   - [Ingest](#ingest-endpoints)
   - [Node](#node-endpoints)
   - [Evolve](#evolve-endpoints)
   - [Events](#events-endpoints)
   - [Metrics](#metrics-endpoints)
   - [Admin](#admin-endpoints)
4. [SSE Event Stream](#sse-event-stream)
5. [Data Types](#data-types)
6. [Error Handling](#error-handling)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FAIM-Native API                          │
│                        FastAPI + Uvicorn                        │
├─────────────────────────────────────────────────────────────────┤
│  Middleware Stack (order matters)                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. SecurityHeaders  │ HSTS, CSP, X-Frame-Options           ││
│  │ 2. JWTAuth          │ NextAuth token verification          ││
│  │ 3. TenantAuth       │ API key + tenant ID validation       ││
│  │ 4. RateLimit        │ Per-endpoint rate limiting           ││
│  │ 5. RequestId        │ X-Request-Id injection               ││
│  │ 6. CORS             │ Cross-origin configuration           ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  9 Routers │ 19 Endpoints                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Authentication

### Option 1: JWT Bearer Token (Recommended for Frontend)

```http
Authorization: Bearer <jwt_token_from_nextauth>
```

The JWT is issued by NextAuth after OTP verification. Contains:
- `sub`: User ID
- `email`: User email
- `graph_id`: Default graph ID (U:xxxxxxxx)
- `tenant_id`: Multi-tenant scope

### Option 2: API Key (For Integrations)

```http
X-Tenant-Id: tenant_abc123
X-Api-Key: sk_faim_xxxxxxxxxxxx
```

---

## API Endpoints

### Health Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Liveness check |
| GET | `/ready` | None | Readiness check (DB + migrations) |
| GET | `/version` | None | Build info |

#### GET /health
```json
// Response: 200 OK
{
  "status": "ok",
  "timestamp": "2026-01-20T18:00:00.000Z"
}
```

#### GET /ready
```json
// Response: 200 OK (or 503 if not ready)
{
  "status": "ready",
  "db_connected": true,
  "tables_ok": true,
  "migrations_ok": true,
  "latest_migration": 10,
  "applied_migration": 10
}
```

#### GET /version
```json
// Response: 200 OK
{
  "version": "0.10.0",
  "stage": "10",
  "faim_native": true,
  "schema": {
    "vector": "v1",
    "dimension": 256,
    "events": "v1",
    "snapshots": "v1",
    "migrations": true
  },
  "features": {
    "multi_tenant": true,
    "sse_events": true,
    "strict_mode": true,
    "index_fallback": true,
    "rate_limiting": true,
    "idempotency": true,
    "durable_jobs": true
  }
}
```

---

### Auth Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/otp/request` | None | Request OTP email |
| POST | `/api/v1/auth/otp/verify` | None | Verify OTP code |

#### POST /api/v1/auth/otp/request

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response: 200 OK**
```json
{
  "success": true,
  "message": "Verification code sent to your email"
}
```

**Error: 429 Too Many Requests**
```json
{
  "detail": "Too many requests. Please wait 15 minutes."
}
```

**Security:**
- Rate limited: 3 requests per 15 minutes per email
- OTP stored as salted hash (never plaintext)
- 6-digit cryptographically secure OTP

#### POST /api/v1/auth/otp/verify

**Request:**
```json
{
  "email": "user@example.com",
  "code": "123456",
  "full_name": "John Doe"  // optional
}
```

**Response: 200 OK**
```json
{
  "success": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "John Doe",
    "graph_id": "U:550e8400"
  }
}
```

**Error: 429 Account Locked**
```json
{
  "success": false,
  "message": "Account locked for 30 minutes due to too many failed attempts."
}
```

**Security:**
- Brute force protection: 5 failed attempts = 30 min lockout
- OTP expires after 10 minutes
- Single-use (deleted after verification)

---

### Query Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/query` | Required | Query graph with FAIM physics |

#### POST /v1/query

**Request:**
```json
{
  "graph_id": "U:550e8400",
  "query_text": "What is machine learning?",
  "k": 10,
  "profile": "STRICT",  // STRICT | RELAXED | FAST
  "return_explain": false
}
```

**Response: 200 OK**
```json
{
  "tenant_id": "tenant_abc",
  "graph_id": "U:550e8400",
  "graph_version": 42,
  "graph_hash": "abc123def456",
  "query_hash": "q:xyz789",
  "k": 10,
  "profile": "STRICT",
  "results": [
    {
      "node_id": "n:123",
      "vector_hash": "v:abc",
      "score": 0.89,
      "score_components": {
        "sim": 0.85,
        "novel": 0.12,
        "opp": 0.02,
        "red": 0.05,
        "rec": 0.08,
        "use": 0.03,
        "lvl": 0.01
      },
      "level": 2,
      "touch_count": 15,
      "evidence": {
        "raw_id": "r:doc1",
        "block_id": "b:para3",
        "anchor": {"page": 1, "line": 42}
      }
    }
  ],
  "metrics": {
    "node_count": 1500,
    "avg_touch": 8.2,
    "CR": 0.78,
    "R": 0.12,
    "D_hat": 1.42,
    "H_hat": 2.31,
    "lambda_hat": 0.89,
    "novelty": 0.15,
    "energy": 0.67
  },
  "duration_ms": 45.2
}
```

**Scoring Formula:**
```
score = w_sim * sim 
      + w_novel * novel 
      - w_opp * opp 
      - w_red * red 
      + w_rec * rec 
      + w_use * use 
      - w_lvl * lvl
```

---

### Ingest Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/ingest` | Required | Ingest via JSON (base64) |
| POST | `/v1/ingest/upload` | Required | Ingest via multipart |

#### POST /v1/ingest (JSON)

**Request:**
```json
{
  "graph_id": "U:550e8400",
  "filename": "document.pdf",
  "bytes_base64": "JVBERi0xLjQK...",
  "profile": "strict",
  "persist_mode": "relaxed"
}
```

**Response: 200 OK**
```json
{
  "status": "ok",
  "packet_hash": "p:sha256abc...",
  "graph_version": 43,
  "nodes_written": 25,
  "merges": 3,
  "block_count": 12,
  "vector_count": 25,
  "events_emitted": ["INGEST_START", "NODE_CREATED", "INGEST_COMPLETE"],
  "latency_ms": 1250
}
```

#### POST /v1/ingest/upload (Multipart)

**Request:**
```
Content-Type: multipart/form-data

graph_id: U:550e8400
profile: strict
persist_mode: relaxed
file: (binary file data)
```

**Response:** Same as JSON endpoint.

**Idempotency:**
- `packet_hash` is the idempotency key
- Re-ingesting same content returns cached result

---

### Node Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/node/{node_id}` | Required | Get node details |
| GET | `/v1/node/{node_id}/explain` | Required | Get node provenance |

#### GET /v1/node/{node_id}?graph_id=...

**Response: 200 OK**
```json
{
  "node_id": "n:123",
  "graph_id": "U:550e8400",
  "kind": "memory",
  "level": 2,
  "vector_hash": "v:abc",
  "residual": 0.15,
  "touch_count": 15,
  "raw_id": "r:doc1",
  "block_id": "b:para3",
  "anchor": {"page": 1, "line": 42},
  "opp_signature": null,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-20T14:45:00Z"
}
```

#### GET /v1/node/{node_id}/explain?graph_id=...

**Response: 200 OK**
```json
{
  "node_id": "n:123",
  "parents": [
    {"parent_id": "n:100", "fraction": 0.6, "kind": "macro"},
    {"parent_id": "n:101", "fraction": 0.4, "kind": "memory"}
  ],
  "fractions_sum": 1.0,
  "recent_events": [
    {"seq": 450, "kind": "INHERIT", "ts": "2026-01-20T14:00:00Z"},
    {"seq": 445, "kind": "TOUCH", "ts": "2026-01-20T13:55:00Z"}
  ]
}
```

---

### Evolve Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/evolve` | Required | Run evolution cycle |

#### POST /v1/evolve

**Request:**
```json
{
  "graph_id": "U:550e8400",
  "profile": "strict",
  "persist_mode": "relaxed"
}
```

**Response: 200 OK**
```json
{
  "status": "ok",
  "graph_version": 44,
  "merges": 8,
  "prunes": 2,
  "diagnostics": {
    "D_before": 1.38,
    "D_after": 1.42,
    "entropy_delta": -0.05,
    "pressure_reduced": true
  },
  "events_emitted": ["EVOLVE_START", "MERGE", "PRUNE", "EVOLVE_COMPLETE"],
  "latency_ms": 3200
}
```

---

### Events Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/events` | Required | List events (paginated) |
| GET | `/v1/events/latest` | Required | Get latest event info |
| GET | `/v1/events/stream` | Required | SSE real-time stream |

#### GET /v1/events?graph_id=...&after_seq=0&limit=50

**Response: 200 OK**
```json
{
  "graph_id": "U:550e8400",
  "tenant_id": "tenant_abc",
  "events": [
    {
      "seq": 100,
      "id": "e:uuid7",
      "kind": "INGEST_START",
      "ts": "2026-01-20T14:00:00Z",
      "payload": {"filename": "doc.pdf"},
      "checksum": "sha256:abc..."
    }
  ],
  "has_more": true,
  "next_seq": 150,
  "count": 50
}
```

#### GET /v1/events/stream?graph_id=...&after_seq=0

**Response: SSE Stream**
```
id: 101
event: INGEST_COMPLETE
data: {"seq": 101, "kind": "INGEST_COMPLETE", ...}

event: ping
data: {"ts": "2026-01-20T14:05:00Z", "last_seq": 101}
```

See [SSE Event Stream](#sse-event-stream) for details.

---

### Metrics Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/metrics/scorecard` | Required | Get graph metrics |

#### GET /v1/metrics/scorecard?graph_id=...

**Response: 200 OK**
```json
{
  "graph_id": "U:550e8400",
  "graph_version": 44,
  "graph_hash": "abc123",
  "dimension_D": 1.42,
  "entropy_H": 2.31,
  "pressure_lambda": 0.89,
  "node_count": 1500,
  "edge_count": 4200,
  "redundancy": 0.12,
  "novelty": 0.15,
  "energy": 0.67,
  "computed_at": "2026-01-20T14:30:00Z"
}
```

---

### Admin Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/admin/reindex` | Admin Key | Rebuild vector index |
| POST | `/v1/admin/snapshot/create` | Admin Key | Create snapshot |
| POST | `/v1/admin/snapshot/restore` | Admin Key | Restore snapshot |
| POST | `/v1/admin/replay/verify` | Admin Key | Verify determinism |

**Admin Auth:**
```http
X-Admin-Key: <admin_secret_key>
```

#### POST /v1/admin/reindex

**Request:**
```json
{"graph_id": "U:550e8400"}
```

**Response:**
```json
{
  "status": "completed",
  "message": "Reindexed 1500 nodes",
  "details": {"node_count": 1500}
}
```

---

## SSE Event Stream

The `/v1/events/stream` endpoint provides real-time updates.

### Event Types

| Event Kind | Payload | Description |
|------------|---------|-------------|
| `INGEST_START` | `{filename, raw_id}` | File ingest begun |
| `INGEST_COMPLETE` | `{packet_hash, nodes}` | File ingest finished |
| `NODE_CREATED` | `{node_id, kind, level}` | New node created |
| `NODE_MERGED` | `{src_id, dst_id}` | Nodes merged |
| `NODE_PRUNED` | `{node_id, reason}` | Node pruned |
| `EVOLVE_START` | `{version_before}` | Evolution cycle started |
| `EVOLVE_COMPLETE` | `{merges, prunes}` | Evolution finished |
| `QUERY_START` | `{query_hash}` | Query started |
| `QUERY_COMPLETE` | `{k, duration_ms}` | Query finished |
| `DIAGNOSTICS_SNAPSHOT` | `{graph_hash, metrics}` | Metrics snapshot |
| `ping` | `{ts, last_seq}` | Heartbeat (every 15s) |
| `timeout` | `{message}` | Stream timeout (5 min) |
| `disconnect` | `{last_seq}` | Clean disconnect |

### Client Usage (JavaScript)

```javascript
const eventSource = new EventSource(
  '/v1/events/stream?graph_id=U:550e8400&after_seq=0'
);

eventSource.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log(`Event ${data.kind}:`, data);
};

eventSource.addEventListener('INGEST_COMPLETE', (e) => {
  const data = JSON.parse(e.data);
  showNotification(`Ingested: ${data.payload.filename}`);
});

eventSource.onerror = () => {
  // Reconnect with last known seq
  reconnect(lastSeq);
};
```

---

## Data Types

### Core Types

| Type | Description |
|------|-------------|
| `UUID7` | Time-ordered, 48-bit timestamp + random |
| `GraphId` | String format `U:xxxxxxxx` |
| `Sha256Hex` | 64-char hex hash |
| `Vector256` | 256-dimensional float array |

### Node Kinds

| Kind | Level | Description |
|------|-------|-------------|
| `memory` | 0 | Atomic memory from raw content |
| `cluster` | 1 | Grouped memories |
| `macro` | 2+ | Higher-level abstractions |
| `invention` | 3+ | AI-discovered concepts |

### Edge Types

| Type | Description |
|------|-------------|
| `INHERIT` | Parent → child inheritance |
| `OPPOSE` | Antisymmetric opposition |
| `SIMILAR` | Semantic similarity |

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid params) |
| 401 | Unauthorized (missing auth) |
| 403 | Forbidden (invalid auth) |
| 404 | Resource not found |
| 429 | Rate limited |
| 500 | Internal server error |
| 503 | Service unavailable |

### Error Response Format

```json
{
  "detail": "Human-readable error message"
}
```

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/auth/otp/request` | 3/15min per email |
| `/v1/query` | 100/min per tenant |
| `/v1/ingest` | 50/min per tenant |
| `/v1/evolve` | 10/min per tenant |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `QDRANT_URL` | No | Vector index URL |
| `REDIS_URL` | No | Cache URL |
| `NEXTAUTH_SECRET` | Yes | JWT signing secret |
| `RESEND_API_KEY` | Yes | OTP email delivery |
| `FAIM_AUTO_MIGRATE` | No | Auto-run migrations on startup |
| `FAIM_LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR |

---

## Frontend Integration

### Next.js API Proxy

The frontend proxies API requests through `/api/v1/*`:

```typescript
// lib/api.ts
export async function queryGraph(graphId: string, query: string) {
  const res = await fetch('/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      graph_id: graphId,
      query_text: query,
      k: 10,
      profile: 'STRICT'
    })
  });
  return res.json();
}
```

### SSE in React

```tsx
import { useEffect, useState } from 'react';

export function useGraphEvents(graphId: string) {
  const [events, setEvents] = useState([]);
  
  useEffect(() => {
    const es = new EventSource(`/api/v1/events/stream?graph_id=${graphId}`);
    
    es.onmessage = (e) => {
      setEvents(prev => [...prev, JSON.parse(e.data)]);
    };
    
    return () => es.close();
  }, [graphId]);
  
  return events;
}
```

---

## Endpoint Summary

| Router | Endpoints | Auth Required |
|--------|-----------|---------------|
| Health | 3 | No |
| Auth | 2 | No |
| Query | 1 | Yes |
| Ingest | 2 | Yes |
| Node | 2 | Yes |
| Evolve | 1 | Yes |
| Events | 3 | Yes |
| Metrics | 1 | Yes |
| Admin | 4 | Admin Key |
| **Total** | **19** | |

---

*Generated: 2026-01-20*  
*FAIM-Native v0.10.0*
