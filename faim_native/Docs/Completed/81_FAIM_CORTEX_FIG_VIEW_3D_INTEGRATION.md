# 81 - FAIM Cortex & FIG View 3D Integration Spec

## 1. Status
Completed for the current FAIM runtime contract.

FAIM now connects Cortex reasoning to FIG View visualization through a shared
query-explain and interaction-ledger surface. The 3D graph view is real, the
overlay modes are real, and the pulse-v2 proof path is real.

## 2. What is real

- Cortex query turns emit structured reasoning state
- query explain payloads expose graph hops, temporal labels, and lineage
- FIG View consumes the same explanation state for canvas glow, path motion,
  inspector proof, relation traces, and legends
- FIG interaction events are journaled as append-only `FIG_INTERACTION`
  records
- overlay modes and timeline state are surfaced in the live UI

## 3. What this integration actually means

This is not a fake “mind simulation” layer.
It is a real integration between:

- Cortex query/reasoning state
- graph/query explain payloads
- FIG View canvas rendering
- interaction journaling

The user sees the current reasoning path, the active node set, the relation
path, the timeline state, and the associated proof surfaces in the 3D graph UI.

## 4. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/core/query/pulse_protocol.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`
- `/home/sephi-asi/FAIM/faim_native/api/routers/graph.py`
- `/home/sephi-asi/FAIM/faim_native/api/routers/events.py`
- `/home/sephi-asi/FAIM/frontend/src/contexts/ChatContext.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigViewPage.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigCanvas.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigInspector.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigRelationPanel.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigLegend.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigPulseTrace.tsx`

## 5. Runtime truth

What the user can expect:

- exact traversal paths can light up in FIG View
- pulse-v2 ledgers explain why nodes glow
- timeline and overlay state are visible in the graph UI
- path, relation, and inspector views reuse the same backend proof

What this is not:

- it is not a separate always-on websocket telemetry service
- it is not a fake-only spec without backend wiring
- it is not a full autonomous cognition simulator beyond the shipped runtime

## 6. What is left

No major runtime gap remains for the current shipped integration.
The remaining work is only documentation truth-tightening and file
organization.

## 7. Validation

Validated by:

- `python3 -m pytest tests/acceptance/test_AT_fig_interaction_pulse_write.py tests/acceptance/test_AT_fig_graph_api_surface.py tests/acceptance/test_AT_Q7_query_flow.py tests/acceptance/test_AT_semantic_fusion_determinism.py -q`

Current result:

- backend acceptance checks passed

---

*Status: Completed and reconciled to runtime truth*
