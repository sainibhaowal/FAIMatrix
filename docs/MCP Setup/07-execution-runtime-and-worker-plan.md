# Phase 07 - Execution Runtime and Worker Plan

## What to do
Build the runtime that actually executes MCP tool calls through FAIM’s
orchestration system.

## Why to do it
The marketplace is only useful if tool calls can run reliably, safely, and
asynchronously when needed.

## Where to do it
Likely files:
- `faim_native/orchestration/jobs/worker.py`
- `faim_native/orchestration/jobs/job_store.py`
- `faim_native/orchestration/self_evolve_scheduler.py`
- `faim_native/orchestration/query_flow.py`
- `faim_native/orchestration/evolve_flow.py`
- `faim_native/core/cortex/runtime.py`
- `faim_native/core/cortex/planner.py`
- `faim_native/core/cortex/branches.py`
- `faim_native/core/cortex/reducer.py`

## Runtime responsibilities
- Accept an execution request from broker/policy.
- Resolve connector credentials securely.
- Run the correct tool call or job.
- Capture outputs, errors, latency, and audit state.
- Feed meaningful results back into Cortex or memory writeback proposals.

## Exact execution path
1. UI or Cortex proposes a connector action.
2. Backend broker validates tenant, connector, tool, scope, and policy.
3. Broker creates a `mcp_connector_run` row.
4. If safe and fast, broker may execute synchronously.
5. If long-running, risky, or retryable, broker enqueues a worker job.
6. Worker loads encrypted credentials, executes the tool, and records events.
7. Broker finalizes run state and exposes sanitized result to the caller.

## Chat vs background jobs
- Direct chat path:
  - read-only lookups,
  - lightweight discovery,
  - small safe tool calls,
  - immediate response preferred.
- Background job path:
  - write actions,
  - multi-step workflows,
  - token refresh,
  - retries,
  - connector sync,
  - memory writeback proposals.

## Installation lifecycle
- `cataloged` -> `install_pending` -> `oauth_pending` -> `connected`
- `connected` -> `suspended` when policy or provider temporarily blocks access
- `connected` -> `revoked` when user/admin disconnects
- `connected` -> `error` for unrecoverable runtime failures
- `revoked` can return to `install_pending` only via a fresh reinstall

## Execution modes
- synchronous for small safe reads
- queued async for long-running or risky actions
- approval-gated for write or external side effects
- policy-denied for unsupported or unsafe requests
- retryable for transport or temporary provider failures

## Safety rules
- Tool execution must never bypass authentication.
- Long-running work must be interruptible and auditable.
- Results must be redacted before being stored or displayed.

## Failure handling
- Retry only idempotent actions.
- Distinguish auth failure, transport failure, provider failure, and policy
  denial.
- Preserve execution trace for debugging and user review.
- Auto-refresh tokens only when a refresh token exists and the connector policy
  allows it.
- Mark a connector `suspended` after repeated auth failures until reconnected.
- Mark runs with explicit terminal statuses: `success`, `failed`, `denied`,
  `cancelled`, `retrying`, `needs_approval`.
