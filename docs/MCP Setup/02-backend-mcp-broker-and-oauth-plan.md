# Phase 02 - Backend MCP Broker and OAuth Plan

## What to do
Build the backend control plane for:
- connector catalog APIs,
- OAuth connect / callback / refresh / revoke flows,
- brokered tool execution,
- policy checks before execution,
- audit logging and job enqueueing.

## Why to do it
FAIM Cortex should choose and supervise actions, but the backend must enforce
security, tenant isolation, and approval policy before any external app is
touched.

## Where to do it
Likely backend files:
- `faim_native/api/routers/`
- `faim_native/api/middleware/auth.py`
- `faim_native/api/deps.py`
- `faim_native/orchestration/jobs/worker.py`
- `faim_native/orchestration/jobs/job_store.py`
- `faim_native/orchestration/self_evolve_scheduler.py`
- `faim_native/store/pg/repos/`
- `faim_native/store/crypto/envelope.py`

## API surface to add
- `GET /api/v1/mcp/catalog`
- `GET /api/v1/mcp/installations`
- `POST /api/v1/mcp/installations`
- `GET /api/v1/mcp/installations/{id}`
- `PATCH /api/v1/mcp/installations/{id}`
- `POST /api/v1/mcp/installations/{id}/oauth/start`
- `GET /api/v1/mcp/installations/{id}/oauth/callback`
- `POST /api/v1/mcp/installations/{id}/refresh`
- `POST /api/v1/mcp/installations/{id}/revoke`
- `POST /api/v1/mcp/connectors/{id}/execute`
- `GET /api/v1/mcp/runs`
- `GET /api/v1/mcp/runs/{run_id}`
- `GET /api/v1/mcp/runs/{run_id}/events`
- `POST /api/v1/mcp/runs/{run_id}/approve`
- `POST /api/v1/mcp/runs/{run_id}/cancel`

## Initial connector protocol choice
- Start with HTTP-based MCP-compatible servers that expose JSON tool schemas.
- Add a compatibility adapter that translates catalog/tool metadata into FAIM
  internal contracts.
- Keep the adapter isolated so future transport variants do not affect the
  broker or UI.

## Initial OAuth provider list
- Generic OAuth 2.0 / OIDC providers for marketplace servers.
- First-class support should be planned for the connector types FAIM actually
  ships with the catalog, but the backend should remain provider-agnostic.
- Each provider integration must define:
  - auth endpoint
  - token endpoint
  - refresh endpoint
  - revocation endpoint
  - scopes
  - callback constraints

## Exact callback handling
- Use `state` to bind tenant, graph, installation, and nonce.
- Validate callback origin and redirect URI.
- Reject callbacks that do not match a pending installation record.
- Persist only the minimum required OAuth subject, expiry, and token metadata.
- Exchange, encrypt, and store tokens server-side before redirecting back.

## Broker responsibilities
- Validate tenant and scopes.
- Resolve install state and token state.
- Encrypt / decrypt connector secrets safely.
- Redact secrets from logs and events.
- Queue long-running connector actions to worker jobs.
- Block sensitive actions until approved.
- Resolve whether a tool is safe to run synchronously, must be queued, or
  must be denied.
- Enforce per-tool allowlists and per-connector risk levels.
- Expose only sanitized run status to the browser.

## OAuth safety rules
- Use state / nonce / redirect validation.
- Bind callback to tenant and installation record.
- Support token refresh and revocation.
- Never expose raw provider tokens to the browser after initial grant.

## Runtime safety rules
- The broker, not the UI, decides whether a tool call is permitted.
- The worker executes only allowed queued actions.
- Cortex can propose actions, but policy can still deny or defer them.
- Direct chat can request tool use, but the broker converts that request into
  an installation-aware, policy-checked execution plan.
