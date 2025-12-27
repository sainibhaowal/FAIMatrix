# FAIM Product Contract — Universe Graph + SSE

## 0) Graph Policy (Production Rule)

### Universe graph_id
- **Graph ID = one user “Universe”** (default).
- In **production**, backend derives `graph_id` automatically per user:
  - `graph_id = "U:" + sha256(user_id)[:12]`
- Frontend **never** asks user to type a graph id.

### Dev mode
- `graph_id="MAIN"` by default.
- Dev may pass `?graph_id=...` for testing only.

### Galaxies
- “Galaxies” are **clusters inside the same Universe graph**, not separate graphs.
- Enterprise/multi-tenant may introduce separate graphs later, but default is:
  - 1 user = 1 Universe graph.

---

## 1) SSE Contract (Strict JSON Always)

### Endpoint
- `GET /api/v1/stream`

### Required properties
- SSE payload MUST always be:
  - `data: <json-string>`
- Never send:
  - Python dict repr
  - Double-encoded JSON (e.g. `data: "{...}"`)

### First event (contract)
On connect, server sends:
- `event: contract`
- `id: 0`
- `data: { "universe": { "graph_id": "...", "label": "Universe" }, "galaxies": [], "policy": {...} }`

UI MUST render:
- Universe label = **"Universe"**
- Galaxies are derived from clustering / server events, not hardcoded names.

### Keepalive
- Server emits:
  - `event: ping`
  - every `SSE_KEEPALIVE_SECONDS` (default 15s)
  - JSON data: `{ "ts": <unix>, "graph_id": "<gid>" }`

### Reconnect safety
- Server uses monotonic `id:` per graph.
- If client reconnects with `Last-Event-ID`:
  - server replays events newer than that id if still in bounded replay buffer.
  - if replay gap occurs, server emits:
    - `event: gap`
    - data: `{ "type":"replay_gap", "action":"client_should_resync_state" }`

### Core event types (minimum)
- `contract` — Universe + policy (sent first)
- `ping` — keepalive
- `fig_delta` — graph update deltas
- `chat_token` — streaming chat tokens
- `chat_used` — memory nodes used in a chat turn
- `metrics` — dashboard metrics updates
- `toast` — user-visible notifications
- `error` — structured errors (JSON)

---

## Acceptance

1) `curl -N http://127.0.0.1:8000/api/v1/stream` shows valid SSE:
- `event: contract` + JSON `data: {...}`
- periodic `event: ping` + JSON

2) Frontend EventSource parses every event without try/catch hacks.

3) UI never hardcodes “Ravinder Main”:
- always renders **Universe**
- galaxies shown as clusters inside Universe.
