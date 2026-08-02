# Phase 09 - Observability, Recovery, and Audit Plan

## What to do
Add durable tracing, logging, audit, and recovery mechanics for MCP
connector activity.

## Why to do it
Connector systems fail in messy ways. FAIM needs enough observability to
recover, replay, and explain what happened.

## Where to do it
Likely files:
- `faim_native/api/services/`
- `faim_native/api/middleware/`
- `faim_native/orchestration/jobs/job_store.py`
- `faim_native/orchestration/jobs/worker.py`
- `faim_native/store/pg/repos/`
- `faim_native/store/pg/models_faim.py`
- `frontend/src/components/`

## Observability requirements
- request id propagation
- connector run id propagation
- tenant and graph scope logging
- audit entries for install/connect/revoke/execute
- redacted structured logs
- operator-friendly failure summaries
- latency and retry counters per connector
- per-tool success and failure rates
- token refresh success/failure counts
- approval queue size and age
- worker health and backlog metrics

## Recovery requirements
- resume stalled jobs
- detect token expiry and refresh failures
- handle connector revocation cleanly
- preserve partial failures and rollback indicators
- replay safe read actions when idempotent
- quarantine connectors with repeated auth or protocol failures
- surface a manual retry path only where policy allows
- preserve the last safe connector state snapshot

## Audit requirements
- who installed
- who connected
- who approved
- what scopes were granted
- what tool ran
- what memory changed
- what failed and why
- when token refresh occurred
- when revocation occurred
- whether action was direct, queued, or approved
- whether Cortex proposed the action or a user initiated it
