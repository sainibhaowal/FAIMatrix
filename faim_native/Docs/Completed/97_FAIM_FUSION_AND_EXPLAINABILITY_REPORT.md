# Phase F: Fusion and Explainability Report

## Status

Implemented and validated.

## What changed

- FAIM now emits a structured `fusion_summary` for ranked query results.
- The summary is based on the real active ranking layers, not a synthetic after-the-fact description.
- Query explain payloads now include:
  - `fusion_summary` for the current ranked node
  - `query_fusion_summary` for the overall retrieval path
- The structured fusion summary tracks:
  - core score
  - active layers
  - per-layer score contribution
  - strongest layers on the winning result
  - strongest raw retrieval signals on the winning result
- Cortex now carries this retrieval summary into `brain_state.retrieval_summary`.
- The Cortex state UI now shows a dedicated retrieval-fusion section so users can see which retrieval layers were active on the winning answer and how large the candidate pool was.

## Safety properties

- Contract-safe: no route names were changed.
- Backward-safe: result `explain` remains a dictionary surface, now with richer structure.
- Deterministic: fusion summaries are derived from deterministic ranking math already used in the engine.
- Additive: this does not replace the ranking engine, only explains it better.

## Real effect

Before Phase F:

- query explainability existed, but the story was scattered across separate sections
- Cortex carried the answer and reasoning tree, but not a concise retrieval-fusion summary
- the UI did not show a clean “why this won” retrieval-layer readout

After Phase F:

- every explained result can show which fusion layers were active
- query-level explainability can show candidate-pool shape and expansion sources
- Cortex can expose the retrieval fusion story directly in structured state
- users can inspect the winning result’s active retrieval layers without reading raw internal payload noise

## Files involved

- `faim_native/core/query/query_engine.py`
- `faim_native/orchestration/query_flow.py`
- `faim_native/core/cortex/runtime.py`
- `faim_native/core/cortex/reducer.py`
- `faim_native/core/cortex/schemas.py`
- `frontend/src/components/memoryquery/CortexStatePanel.tsx`
- `frontend/src/contexts/ChatContext.tsx`
- `tests/acceptance/test_AT_Q5_explain_correctness.py`
- `tests/acceptance/test_AT_CORTEX_turn.py`

## Validation

- focused explain/cortex acceptance tests passed
- frontend typecheck passed

Phase F is complete when:

- explained query results expose structured fusion summaries
- Cortex brain state carries retrieval summary data
- the UI surfaces the retrieval-fusion story clearly
- tests confirm both query explainability and Cortex integration
