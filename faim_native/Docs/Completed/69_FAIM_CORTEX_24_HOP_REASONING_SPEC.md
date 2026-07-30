# 69 - FAIM Cortex Adaptive 1-24+ Hop Reasoning Runtime

## Executive Summary

FAIM Cortex now implements a **real planner-driven adaptive hop runtime** instead of a documentation-only 24-hop claim.

The live system does the following:

- runs Cortex structured thinking **on by default** from the backend; the old `think_enabled` request field is now only a backward-compatible client hint
- plans a bounded hop budget per turn in [`faim_native/core/cortex/planner_enhanced.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/planner_enhanced.py)
- uses that budget to scale graph-semantic retrieval in [`faim_native/core/cortex/runtime.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/runtime.py) and [`faim_native/orchestration/query_flow.py`](/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py)
- executes an exact bounded traversal branch in [`faim_native/core/cortex/branches.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/branches.py) through [`faim_native/core/reasoning/traversal.py`](/home/sephi-asi/FAIM/faim_native/core/reasoning/traversal.py)
- persists the structured reasoning result with exact path metadata in the normal Cortex turn snapshot flow
- surfaces the exact path to FIG View through [`frontend/src/contexts/ChatContext.tsx`](/home/sephi-asi/FAIM/frontend/src/contexts/ChatContext.tsx)

Default bounded production ceiling:

- `1..24` hops by default
- configurable up to `128` through `FAIM_CORTEX_MAX_HOPS`

This is not unbounded search. It is a **bounded, deterministic, pruned, auditable graph reasoning runtime**.

## What Is Real Now

### 1. Adaptive hop budgets are live

The enhanced planner now computes a deterministic hop budget from:

- query complexity
- task type
- causal / temporal / dependency indicators
- query size
- configured maximum hop ceiling

Current implementation:

- default ceiling: `24`
- configurable ceiling: `FAIM_CORTEX_MAX_HOPS`
- file: [`faim_native/core/cortex/planner_enhanced.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/planner_enhanced.py)

This means FAIM can legitimately operate in:

- `1` hop for simple direct turns
- low/mid depth for moderate turns
- deeper multi-hop for investigative turns
- `24+` only when explicitly configured and still bounded

The user no longer needs to press a chat `THINK` button for this behavior. The Cortex API routes every turn through the enhanced planner by default, including turns from older clients that still send `think_enabled: false`.

### 2. Planner budgets now drive retrieval

Before this implementation, the planner described multi-hop depth but the query runtime still used hardcoded shallow graph expansion.

Now the Cortex runtime computes retrieval options from the planned turn and passes them into the live query flow.

Key file:

- [`faim_native/core/cortex/runtime.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/runtime.py)

The query engine and query flow now accept adaptive graph-semantic controls:

- `graph_max_hops`
- `graph_max_neighbors`
- `graph_decay`
- `graph_alpha`
- `graph_diffusion_steps`

Files:

- [`faim_native/orchestration/query_flow.py`](/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py)
- [`faim_native/core/query/query_engine.py`](/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py)

### 3. Exact traversal branch is live

The Cortex reasoning tree now includes a real `traversal` branch.

That branch:

- uses the current turn’s hop budget
- uses planner constraints when available
- runs the bounded traversal engine
- returns exact path metadata
- returns the strongest partial path if no exact goal match survives the guards

Files:

- [`faim_native/core/cortex/branches.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/branches.py)
- [`faim_native/core/reasoning/traversal.py`](/home/sephi-asi/FAIM/faim_native/core/reasoning/traversal.py)

### 4. Traversal engine now supports real deeper bounded search

The traversal engine was hardened to support real deeper runtime behavior:

- default max hops raised from `3` to `24`
- exact stored edge weights normalized correctly
- broken node-model import path fixed
- deterministic frontier pruning added
- max frontier width added
- max total expansions added
- partial-path fallback added
- exact `node_ids` and `edge_ids` added to path metadata

This makes the engine usable for genuine bounded reasoning instead of being stuck as a shallow helper.

### 5. FIG View now prefers exact traversal paths

When Cortex returns a traversal branch with exact path metadata, the chat context now uses that path for FIG highlighting instead of only building an approximate overlay from evidence nodes.

File:

- [`frontend/src/contexts/ChatContext.tsx`](/home/sephi-asi/FAIM/frontend/src/contexts/ChatContext.tsx)

## Engineering Boundaries

This implementation is intentionally **production-bounded**, not “infinite intelligence”.

The runtime protects itself with:

- cycle prevention
- deterministic sorting
- branching-factor limits
- frontier-width pruning
- maximum total expansion limits
- confidence decay
- contradiction-aware graph-semantic suppression
- tenant and graph scoping

These controls are necessary because naive graph search grows combinatorially with hop depth.

In other words:

- deeper hops are now real
- but they are still governed by bounded search math

## What The Claim Means Now

### Honest claim

FAIM Cortex supports:

- adaptive bounded reasoning from `1..24` hops by default
- configurable bounded ceilings above `24`
- planner-driven retrieval depth
- exact traversal-path execution
- deterministic and auditable path outputs

### What it does not mean

It does **not** mean:

- unbounded graph crawling
- guaranteed exact goal hits at every depth
- zero-latency traversal at arbitrary branching factors
- infinite autonomous inference

If no exact route survives the constraints, FAIM returns the strongest bounded partial route instead of hallucinating.

## Validation Evidence

The implementation is backed by live tests:

- Cortex unit/runtime coverage in [`tests/unit/test_cortex_runtime.py`](/home/sephi-asi/FAIM/tests/unit/test_cortex_runtime.py)
- traversal-depth coverage in [`tests/unit/test_reasoning_traversal.py`](/home/sephi-asi/FAIM/tests/unit/test_reasoning_traversal.py)
- Cortex route and persistence coverage in [`tests/acceptance/test_AT_CORTEX_turn.py`](/home/sephi-asi/FAIM/tests/acceptance/test_AT_CORTEX_turn.py)

Verified behaviors include:

- adaptive hop budget allocation
- traversal beyond three hops
- partial-path fallback when exact goal match is unavailable
- structured traversal branch persistence
- Cortex turn API compatibility

## Practical Runtime Interpretation

For simple memory questions:

- FAIM stays shallow
- usually `1..3` hops

For more investigative graph questions:

- FAIM expands the hop budget
- deepens graph-semantic retrieval
- executes an exact traversal branch

For very deep or structurally complex tasks:

- FAIM can use the default `24` hop ceiling
- or a higher configured ceiling if explicitly enabled
- while still honoring bounded frontier and expansion limits

## Final Status

**Status: Implemented as a real bounded adaptive hop runtime**

More precisely:

- production-bounded: yes
- deterministic: yes
- planner-driven: yes
- exact traversal branch: yes
- exact `1..24` default ceiling: yes
- configurable `N` ceiling beyond `24`: yes
- backend thinking default-on: yes
- client-side think toggle required: no
- unbounded / infinite-hop engine: no by design
