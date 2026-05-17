# 67 - FAIM Cortex Runtime Architecture

## Scope

Phase 1 backend Cortex runtime for FAIM.

## Contract

FAIM Cortex is not a raw chat wrapper. It is a structured control loop:

`memory retrieval -> planner -> parallel branches -> reducer -> narrator -> optional consolidation proposal`

## Phase 1 Guarantee

- Existing `/api/v1/query` stays unchanged.
- Cortex uses the query engine as a lower-level memory primitive.
- Cortex returns structured reasoning state, not raw chain-of-thought.
- Cortex keeps tenant isolation and graph scoping on every turn.

## Runtime Surfaces

- `POST /api/v1/cortex/turn`
- `GET /api/v1/cortex/sessions`
- `GET /api/v1/cortex/sessions/{session_id}/turns`
- backend package: `faim_native/core/cortex/`

## Structured State

- `CortexTaskType`
- `CortexReasoningNode`
- `CortexBrainState`
- `CortexTurnRequest`
- `CortexTurnResponse`

## Branches

1. recall
2. timeline
3. contradiction
4. concept
5. prediction
6. provenance

## Safety Rules

- Do not store raw chain-of-thought.
- Do not write memory automatically in Phase 1.
- Do not change the existing query route contract.
- Do not bypass auth or tenant scoping.

## Follow-on Phases

- Phase 2: memory-query UI consumes Cortex turn state
- Phase 3: persistence for sessions / turns / reasoning / writeback candidates
- Phase 4: rollout tests and docs reconciliation

## Status Update

- Phases 1 through 3 are implemented.
- Cortex turns now carry session continuity metadata from prior structured turns.
- Cortex exposes session and turn history endpoints for browserable brain state.
- Validation and documentation reconciliation are captured in `68_FAIM_CORTEX_IMPLEMENTATION_COMPLETION_REPORT.md`.


## Detailed Explanations & Scenario Analysis

### Why is this feature here?
FAIM Cortex exists to transition the platform from a "flat chat wrapper" to a structured, stateful "cognitive control loop". Traditional AI architectures use a single black-box LLM call. FAIM Cortex separates concerns into discrete, traceable steps: memory retrieval, planning, parallel branch execution, reduction, and narration.

### How it works in any scenario
When a user asks a complex question (e.g., "Why did the login fail?"), the Cortex control loop orchestrates the resolution. It plans the query, runs parallel branches (timeline, contradiction, provenance) against the deterministic memory engine, reduces these into a unified `CortexBrainState`, and narrates the answer. This applies universally across coding, finance, or legal domains.

### Comparisons & Differences
Compared to the legacy `/api/v1/query` which simply fetches and summarizes reactively, the Cortex Runtime is proactive. It breaks queries down, executes specialist sub-routines, and proposes writeback updates to the graph database.

### Why it is unique and useful
It forces AI reasoning to occur *outside* opaque neural weights and *inside* an inspectable control loop. This is critical for enterprise compliance, debugging, and establishing trust.

### Future Scenarios
Cortex Runtime paves the way for multi-agent orchestration, where each "branch" is handled by a specialized sub-agent, enabling massive scale inference distribution.
