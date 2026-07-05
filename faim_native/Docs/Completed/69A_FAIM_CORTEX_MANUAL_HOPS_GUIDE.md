# 69A - FAIM Cortex Manual Hops Guide

## Purpose

This guide explains FAIM Cortex hop reasoning in practical human terms.

It is not the low-level implementation spec.  
It is the **operator and product guide** for:

- what a hop is
- how Cortex chooses hop depth
- how FAIM retrieval, graph semantics, and traversal work together
- what users see
- why this architecture is stronger than shallow retrieval systems

Use this guide together with:

- [`69_FAIM_CORTEX_24_HOP_REASONING_SPEC.md`](/home/sephi-asi/FAIM/faim_native/Docs/69_FAIM_CORTEX_24_HOP_REASONING_SPEC.md)
- [`67_FAIM_CORTEX_RUNTIME_ARCHITECTURE.md`](/home/sephi-asi/FAIM/faim_native/Docs/Completed/67_FAIM_CORTEX_RUNTIME_ARCHITECTURE.md)

## What Is a Hop?

A **hop** is one graph step from one node to another through an edge.

Example:

- Node A = `PaymentService`
- Edge = `leads_to`
- Node B = `CheckoutController`

That is **1 hop**.

If Cortex continues:

- `PaymentService` -> `CheckoutController`
- `CheckoutController` -> `CartOrchestrator`
- `CartOrchestrator` -> `GatewayRetryPolicy`

that becomes **3 hops**.

So:

- more hops = deeper structural reasoning
- fewer hops = faster, more local evidence

## What FAIM Does Now

FAIM Cortex now runs **adaptive bounded hop reasoning**:

- default live runtime: `1..24` hops
- configurable bounded ceiling: up to `128`
- deterministic pruning: enabled
- exact traversal path persistence: enabled
- exact graph highlight path to FIG View: enabled when traversal path is present

This means FAIM does not use one fixed depth for every query.

Instead:

- simple question -> shallow route
- complex question -> deeper route
- advanced deployment -> can allow deeper bounded ceilings

## The End-to-End Flow

When a user asks a question, the system now works like this:

### Phase 1 - Query arrives

The user asks something like:

`Why did checkout failures spike after the gateway rollout?`

This enters the Cortex turn runtime.

Main file:

- [`faim_native/core/cortex/runtime.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/runtime.py)

### Phase 2 - Cortex planner classifies the task

The enhanced planner looks at:

- query complexity
- task type
- causal words
- temporal words
- dependency-style words
- overall query size

Main file:

- [`faim_native/core/cortex/planner_enhanced.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/planner_enhanced.py)

The planner decides:

- whether multi-hop is needed
- how deep the hop budget should be
- which traversal goal is most appropriate
- which constraint profile should apply

Examples:

- direct lookup -> `1` hop
- basic compare -> `3..4` hops
- timeline / investigative / dependency chain -> `6..24` hops
- advanced configured deployment -> deeper bounded ceilings if allowed

### Phase 3 - Retrieval scales with the planned depth

The planner no longer acts as a disconnected suggestion layer.

Now the planned hop budget flows into retrieval.

That means the retrieval stage can change:

- graph expansion depth
- neighbor limits
- diffusion steps
- decay and weighting shape

Main files:

- [`faim_native/core/cortex/runtime.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/runtime.py)
- [`faim_native/orchestration/query_flow.py`](/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py)
- [`faim_native/core/query/query_engine.py`](/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py)

### Phase 4 - FAIM retrieves and reranks graph evidence

At retrieval time FAIM combines:

- deterministic native-vector recall
- lexical and phrase support
- graph-semantic expansion
- contradiction suppression
- deterministic reranking

This is important:

FAIM does **not** jump directly into a huge blind traversal.

Instead it first finds:

- strong seed nodes
- nearby graph support
- contradiction-aware candidate expansion
- then reranks grounded candidates

That keeps the system safer and more production-usable.

### Phase 5 - Cortex executes parallel reasoning branches

After evidence is recalled, Cortex runs structured reasoning branches like:

- recall
- traversal
- timeline
- contradiction
- concept
- prediction
- provenance
- continuity

Main file:

- [`faim_native/core/cortex/branches.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/branches.py)

### Phase 6 - Traversal branch runs exact bounded path execution

This is the most important new part.

The `traversal` branch now executes a real bounded path search using:

- hop budget from the planner
- allowed edge-type constraints
- deterministic ordering
- cycle prevention
- frontier width pruning
- max total expansion caps
- confidence decay

Main file:

- [`faim_native/core/reasoning/traversal.py`](/home/sephi-asi/FAIM/faim_native/core/reasoning/traversal.py)

If an exact goal route is found:

- Cortex returns the exact path

If no exact route survives the guards:

- Cortex returns the strongest bounded partial route instead

This is much safer than hallucinating a final connection.

### Phase 7 - Cortex reduces everything into one answer state

The branch outputs are merged into one `CortexBrainState`.

That state contains:

- active facts
- contradictions
- open questions
- predictions
- writeback candidates
- reasoning tree
- traversal output

Main file:

- [`faim_native/core/cortex/reducer.py`](/home/sephi-asi/FAIM/faim_native/core/cortex/reducer.py)

### Phase 8 - Exact path can light up FIG View

If traversal metadata exists, the frontend can use:

- exact `node_ids`
- exact `edge_ids`

for graph highlighting.

Main file:

- [`frontend/src/contexts/ChatContext.tsx`](/home/sephi-asi/FAIM/frontend/src/contexts/ChatContext.tsx)

So the path visualization is more truthful than an approximate overlay.

## Why This Is Powerful

The strength of FAIM hop reasoning is not “bigger number = better”.

The strength is:

- adaptive depth
- deterministic selection
- graph-aware grounding
- exact path persistence
- bounded engineering discipline

That gives FAIM several advantages over shallow retrieval systems.

## FAIM vs Shallow Retrieval

### Plain shallow retrieval

Typical shallow systems do:

- embed the query
- find nearest chunks
- summarize them

That is often enough for:

- simple factual answers
- local document matching

But it gets weaker when the answer depends on structure across multiple objects.

### FAIM bounded hop reasoning

FAIM can:

- retrieve initial evidence
- connect semantically related graph areas
- traverse causal / temporal / relational chains
- preserve contradictions
- show the user how the answer was grounded

This is especially stronger for:

- why-questions
- dependency tracing
- incident investigation
- temporal sequence analysis
- cross-document causal linkage
- graph-native evidence explanation

## What Users Experience

From the user side, this should feel like:

1. Ask a direct question.
2. FAIM chooses an answer path.
3. Simple questions answer quickly with shallow evidence.
4. Harder questions trigger deeper graph work.
5. The answer stays grounded in evidence and path structure.
6. FIG View can highlight the actual graph route when available.

The user does not need to manually choose hop counts for the normal path.

That is the point of the adaptive planner.

## Example Scenarios

### Example 1 - Simple direct memory query

Question:

`What is the current launch date for Project Atlas?`

Expected behavior:

- shallow route
- direct evidence lookup
- maybe `1..3` hops
- citation-first answer

Why shallow is enough:

- the question is asking for one current fact
- local evidence is usually sufficient

### Example 2 - Timeline reconstruction

Question:

`How did the deployment timeline change after the March rollback?`

Expected behavior:

- medium-depth route
- timeline branch active
- temporal edges and older/newer suppression matter
- may need several hops to connect rollout, rollback, patch, and final deployment state

### Example 3 - Causal production debugging

Question:

`Why did checkout failures increase after the gateway release?`

Expected behavior:

- investigative route
- deeper hop budget
- traversal branch tries to connect rollout, config, retry policy, timeout behavior, and downstream failures

This is exactly the kind of question where FAIM is stronger than “fetch similar chunks and summarize”.

### Example 4 - Advanced configured deployment

Question:

`Trace the full downstream dependency and contradiction chain across all known payment, tax, gateway, and ledger services.`

Expected behavior:

- deep route
- default ceiling may already be enough
- if deployment explicitly allows higher bounded ceilings, Cortex can go beyond 24 while still using pruning and expansion guards

This is not for every question.

It is for deployments that intentionally want deeper bounded structural traversal.

## Why 24 Default and 128 Configurable?

### Why 24 by default?

Because it is deep enough to be meaningfully stronger than shallow retrieval while still being manageable as a bounded production runtime.

### Why not infinite depth?

Because graph branching grows too fast.

Without pruning, deep traversal becomes expensive and unstable.

### Why allow 128 by configuration?

Because some advanced environments may want:

- larger dependency graphs
- deeper chain inspection
- specialized investigative workflows

But higher ceilings must remain:

- bounded
- explicitly enabled
- still pruned
- still deterministic

## What Keeps This Production-Grade

The runtime is not “just deeper”.

It is production-grade because it uses:

- deterministic ordering
- bounded hop ceiling
- bounded frontier width
- bounded total expansions
- cycle prevention
- contradiction-aware suppression
- exact path metadata
- tenant and graph isolation

These are the real engineering controls behind the claim.

## When FAIM Is Stronger

FAIM hop reasoning is stronger when:

- the answer spans multiple documents
- the answer depends on relation structure
- the answer depends on time ordering
- the answer depends on contradiction handling
- the user wants inspectable reasoning traces

## When Shallow Still Wins

Shallow routes are still correct when:

- the user wants one fact
- the fact is local and obvious
- there is no need to connect several graph regions

This is why adaptive planning matters.

You do not want every question forced through a deep expensive path.

## What Developers Should Remember

If you are extending this system:

- planner depth must stay connected to runtime execution
- retrieval depth and traversal depth are related but not identical
- exact traversal output should stay structured and auditable
- deeper ceilings must remain bounded and pruned
- UI should prefer exact path metadata over approximations whenever available

## Final Summary

FAIM hop reasoning now works like this:

- question arrives
- Cortex classifies it
- planner chooses hop budget
- retrieval scales with that budget
- traversal executes exact bounded paths
- reasoning state is reduced and persisted
- UI can show the real path

That is why FAIM is stronger than simple fetch-and-summarize systems:

- it can reason structurally
- it can reason deeper when needed
- it stays deterministic
- it stays bounded
- it stays inspectable
