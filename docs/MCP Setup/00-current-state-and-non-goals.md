# Phase 00 - Current State and Non-Goals

## What to do
Document the current state of FAIM providers, auth, and Cortex so the MCP
Marketplace work starts from the real codebase instead of assumptions.

## Why to do it
FAIM already has a provider UI for LLM endpoints, scoped auth, tenant
middleware, and Cortex orchestration. The MCP work must extend these systems
without breaking them.

## Where to do it
- `frontend/src/app/(app)/dashboard/providers/page.tsx`
- `frontend/src/contexts/ProviderContext.tsx`
- `frontend/src/lib/providers.ts`
- `frontend/src/lib/providerDiscovery.ts`
- `faim_native/api/middleware/auth.py`
- `faim_native/api/deps.py`
- `faim_native/api/routers/api_keys.py`
- `faim_native/core/cortex/runtime.py`
- `faim_native/orchestration/jobs/worker.py`

## Existing behavior to preserve
- LLM Providers remain the default and unchanged.
- FAIM auth, tenant scoping, rate limiting, and API key audit remain intact.
- Cortex query flow, memory flow, ingest flow, and evolution flow remain intact.
- Existing jobs and background worker behavior remain intact.

## Non-goals
- Do not replace the LLM provider system.
- Do not move MCP connector state into browser-only localStorage.
- Do not let Cortex store or expose raw third-party secrets directly.
- Do not wire marketplace tools directly to runtime execution without policy.
- Do not try to support every app on day one.
- Do not allow direct browser-to-app privileged execution.
- Do not bypass audit, approval, or tenant scope checks for convenience.

## Safety notes
- Any new connector runtime must be tenant-scoped.
- OAuth tokens and connector credentials must be encrypted at rest.
- Execution must go through a broker / policy layer, not directly from UI.
- FAIM should begin with a curated connector list, not an open wild-west app
  directory.

## Safe rollout principle
- Start with memory-rich and high-value connectors only.
- Prefer read-first integrations before write-capable integrations.
- Expand app coverage only after security, logging, and approval behavior are
  stable.
