# 43 - Evolution Page Operations Guide (Controls, Meaning, Troubleshooting)

Date: 2026-02-20  
Owner: FAIM Native Runtime  
Status: Completed

## Purpose

The Evolution page is an operations surface for one selected graph.

It lets you:

1. Select which graph to inspect.
2. Run a manual evolve cycle for that graph.
3. Observe diagnostics, event timeline, scheduler state, and latest run outcomes.

It does not bypass tenant isolation and does not auto-populate data for a graph that has never received writes/events.

## Run Controls: what each button/field does

1. `Graph id` input
- Draft value only.
- Nothing changes until you apply it.

2. `Apply graph`
- Commits the draft graph id as active graph context.
- Triggers full data reload for that graph:
  - scorecard
  - latest event
  - timeline
  - scheduler status
- It does not run evolution by itself.

3. `Run evolve now`
- Calls `POST /api/v1/evolve` for active graph id.
- Runs one evolve cycle immediately.
- Produces evolve events (start, diagnostics, merge/prune/invention, complete/skip/error).
- Updates `Latest Run Outcome` card for the current browser session.

4. `Profile` (`strict`, `fast`, `relaxed`)
- Sent in evolve request payload.
- Backend resolves requested mode into effective mode (policy resolver is authoritative).
- Runtime meaning (evolution path):
  - `strict`: conservative action budget and thresholds, deterministic-first posture.
  - `fast`: balanced throughput with bounded heuristics.
  - `relaxed`: most aggressive action budget/invention/prune posture.
- Operational note:
  - if `FAIM_PROFILE_PERSIST_COMPAT_MODE=true`, evolve knobs stay inside legacy-safe envelope.
  - requested/effective values are still normalized and returned for observability.

5. `Persist mode` (`relaxed`, `strict`)
- Sent in evolve request payload.
- Backend resolves requested mode into effective mode (policy resolver is authoritative).
- Runtime meaning (evolution completion path):
  - `strict`: evolve completion requires synchronous scheduler-state durability update.
  - `relaxed`: core evolve completion commits first; scheduler-state update is best-effort/non-fatal.
- Response/event fields expose the applied path:
  - `requested_profile`, `requested_persist_mode`
  - `effective_profile`, `effective_persist_mode`
  - `durability_path`

6. `Refresh`
- Forces immediate re-fetch of all cards/panels for active graph.

7. `Auto refresh: On/Off`
- Controls polling loop only for this page view.
- Polls timeline/runtime status periodically when On.

8. `Evolution events only` / `All graph events`
- Filters the timeline display only.
- `Evolution events only` keeps:
  - `DIAGNOSTICS_SNAPSHOT`
  - `EVOLUTION_COMPLETE`
  - `EVOLUTION_SKIPPED`
  - `EVOLUTION_MERGE`
  - `PRUNE_NODE`
  - `EVOLUTION_INVENTION_SUMMARY`
  - `EVOLUTION_INVENTION_ERROR`
- `All graph events` shows all event kinds for the selected graph (still tenant-scoped).

## Cards and panels: what they mean

1. Metric cards (`Fractal D`, `Entropy H`, `Pressure λ`, `Node/Edge`)
- Read from metrics scorecard endpoint for selected graph.
- If no diagnostics snapshot exists yet, fractal values can be `-` while counts still show.

2. `Evolution Timeline`
- Append-only event journal for selected graph.
- Shows newest events with kind/seq/time/summary.
- Empty means there are no events visible for this tenant+graph pair.

3. `Latest Run Outcome`
- Result of manual `Run evolve now` from this UI session.
- Not a historical global log; session-local latest manual run summary.
- Includes requested/effective mode and durability/completion metadata from backend.

4. `Runtime Snapshot`
- Shows graph hash, last diagnostics timestamp, last event seq/kind, and quick event counters.

5. `Scheduler State`
- Read-only view of self-evolve runtime flags and due-evaluation:
  - trigger mode
  - jobs enabled
  - self-evolve/self-invent flags
  - due now + due reason
  - version delta thresholds
  - active job / last enqueued job

## Why the page can look empty even when system is healthy

Common causes:

1. Wrong `graph_id` selected.
2. Tenant isolation: data exists under another tenant, not current auth tenant.
3. No writes/evolve executed yet for that graph.
4. Filter set to evolution-only while only non-evolution events exist.
5. Self-evolve disabled or jobs disabled (autonomous runs will not enqueue).

## Confirmed current state in this environment

Current selected graph observed in runtime logs: `U:621be0f1`.

DB check for that graph returned:

1. events: `0`
2. nodes: `0`
3. edges: `0`

So the page showing empty timeline/cards for that graph is expected behavior, not a rendering defect.

## Production checklist

1. Ensure selected graph id is correct (`Apply graph` after edit).
2. Trigger one write/ingest to that graph (or run evolve manually).
3. Keep `Auto refresh` on while validating.
4. If expecting autonomous behavior, verify env flags:
  - `FAIM_ENABLE_JOBS=true`
  - `FAIM_SELF_EVOLVE_ENABLED=true`
  - `FAIM_SELF_INVENT_ENABLED=true` (if invention desired)
  - Trigger mode compatible with your source (`post_upload`, `periodic`, or `hybrid`).
5. Use scheduler `Due reason` to understand why runs are/are not enqueued.
6. If mode behavior appears unchanged, confirm compatibility flag state:
  - `FAIM_PROFILE_PERSIST_COMPAT_MODE=true` keeps legacy-safe runtime envelope.
  - set `FAIM_PROFILE_PERSIST_COMPAT_MODE=false` to apply full differentiated profile/persist semantics.

## Outcome

This guide is complete:

- the operations surface is documented,
- the controls and troubleshooting flow are explained,
- the current runtime meaning is captured for operators.
