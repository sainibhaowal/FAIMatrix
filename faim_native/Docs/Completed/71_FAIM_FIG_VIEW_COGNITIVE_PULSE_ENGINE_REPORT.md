# 71 - FAIM FIG View Cognitive Pulse Engine Report

## 1. Status
Completed for the current FAIM runtime contract.

FAIM now has a formal `pulse-v2` cognitive pulse protocol that is emitted by
graph path explanation and query-time reasoning. The FIG View consumes the same
reason source ledger in the canvas, inspector, relation drawer, and legend.

## 2. Backend implementation
Source files:
- `/home/sephi-asi/FAIM/faim_native/core/query/pulse_protocol.py`
- `/home/sephi-asi/FAIM/faim_native/api/routers/graph.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`

Implemented backend outputs:
- `pulse_trace.protocol = pulse-v2`
- `pulse_trace.events`
- `reason_source_ledger`
- `pulse_event_stream`
- FIG interaction journal events for live selection / hover / overlay /
  drawer / timeline changes
- deterministic `event_id`
- deterministic `trace_id`
- per-node source summary
- per-node `why_glowing` breakdown

## 3. Event sources covered
The pulse ledger now surfaces:
- semantic signature channels
- weighted expansion sources
- semantic registry contribution
- graph traversal hops
- graph diffusion/path/neighborhood/contradiction score
- reranker components
- late-interaction components
- domain-memory query links and candidate scores
- fusion active layers and strongest layers

## 4. Frontend implementation
Source files:
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigCanvas.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigPulseTrace.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigInspector.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigRelationPanel.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigLegend.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigViewPage.tsx`
- `/home/sephi-asi/FAIM/frontend/src/types/figView.ts`

Implemented visual surfaces:
- pulse-strength node glow
- pulse-strength edge width
- pulse-strength directional particles
- per-node reason source ledger panel
- event stream list
- live FIG interaction pulse summary for selection, hover, overlay, drawer,
  and timeline state
- `why this node glows` explanation
- graph hop and domain proof chips
- legend entries for pulse protocol and query reason stack

## 5. What users see
When a relation path or Cortex query explain payload is available, users can see:
- which expansion sources affected the result
- which hop brought a node into the reasoning path
- which graph score components contributed
- which reranker factors strengthened the node
- which late-interaction units matched
- which domain-memory links contributed
- which semantic signature channels exist on the node

When FIG state changes without a new query explain result, users can still see a
live `pulse-v2` interaction summary for:
- selected node
- hovered node
- overlay mode
- top mode
- active drawer
- timeline step

## 6. Runtime truth
This is a real event-backed FIG explanation layer for:
- graph path explanation
- current Cortex query explain payloads
- selected-node ledger rendering
- relation drawer rendering
- legend rendering
- canvas pulse rendering
- best-effort server-side FIG interaction journaling

It is not a separate websocket telemetry service. It is a deterministic backend
reasoning event protocol attached to the current query and graph explain
contracts.

## 7. Validation
Validated by:
- `pnpm --dir frontend typecheck`
- `python3 -m pytest tests/acceptance/test_AT_fig_graph_api_surface.py tests/acceptance/test_AT_Q7_query_flow.py tests/acceptance/test_AT_semantic_fusion_determinism.py -q`

Current result:
- frontend typecheck passed
- 17 focused backend acceptance checks passed

---
Status: Completed and reconciled to runtime truth.
