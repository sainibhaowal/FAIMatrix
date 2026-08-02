# Phase 04 - Cortex Orchestration and Policy Plan

## What to do
Teach Cortex how to supervise installed MCP connectors as part of a
background orchestration brain:
- decide which connector can be used,
- schedule connector actions,
- inspect outcomes,
- write back safe memory changes,
- retry or escalate failures,
- keep an audit trail.

## Why to do it
Your goal is not a query bot. It is a FAIM brain that can manage its own
memory and operational tasks continuously.

## Where to do it
Likely files:
- `faim_native/core/cortex/runtime.py`
- `faim_native/core/cortex/planner.py`
- `faim_native/core/cortex/branches.py`
- `faim_native/core/cortex/reducer.py`
- `faim_native/core/cortex/schemas.py`
- `faim_native/core/cortex/history.py`
- `faim_native/orchestration/jobs/worker.py`
- `faim_native/orchestration/jobs/job_store.py`
- `faim_native/orchestration/evolve_flow.py`

## Policy requirements
- Hard approval gates for risky actions.
- Tenant and graph scope checks on every connector call.
- Tool execution budgets and rate limits.
- Connector-specific allowlists / denylists.
- Strict logging redaction.

## Cortex integration points
- Add a connector-awareness branch or planner state.
- Surface proposed connector actions as structured writeback candidates.
- Persist execution outcomes into cortex/session history or a related
  connector run trail.

## Safety requirements
- Cortex must never bypass the broker.
- Connector actions must be replayable or auditable.
- Failing connectors should not block normal query or memory operations.

