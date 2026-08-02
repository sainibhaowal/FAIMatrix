# Phase 05 - Testing, Docs, and Release Plan

## What to do
Add a production-grade validation plan and documentation trail for the full
MCP Marketplace feature set.

## Why to do it
The feature touches auth, secrets, worker execution, UI state, and Cortex.
It needs regression gates before any rollout.

## Where to do it
Likely tests and docs:
- `tests/unit/`
- `tests/acceptance/`
- `tests/security/`
- `frontend/tests/`
- `docs/MCP Setup/`
- `faim_native/Docs/`

## Test coverage plan
- Unit tests for catalog, install state, OAuth state handling, secret storage,
  policy gating, and broker redaction.
- API tests for connector install, connect, refresh, revoke, execute, and
  list endpoints.
- Frontend tests for the new Providers toggle and MCP marketplace flows.
- Security tests for tenant isolation, secret leakage, and scope enforcement.
- Worker tests for queued connector execution and failure recovery.

## Verification plan
- Run backend test suites relevant to auth, storage, and orchestration.
- Run frontend typecheck and targeted UI tests.
- Verify no existing LLM provider behavior changed.
- Verify no auth or encryption regression.

## Release plan
- Update docs after implementation.
- Keep rollout additive and feature-flagged if needed.
- Commit in small slices only after verification passes.
- Tag only after the full end-to-end path is working.

