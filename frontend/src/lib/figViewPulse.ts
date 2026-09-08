import type {
  FigInteractionPulse,
  FigNode,
  FigPulseEvent,
  FigQueryExplain,
  FigPulseTrace,
} from "@/types/figView";

type BuildInteractionPulseParams = {
  graphId: string;
  selectedNode: FigNode | null;
  hoveredNode: FigNode | null;
  overlayMode: string | null;
  topMode: string | null;
  activeDrawer: string | null;
  timelineStepIdx: number | null;
  queryExplain?: FigQueryExplain | null;
  pulseTrace?: FigPulseTrace | null;
};

function stablePulseId(parts: Array<string | number | boolean | null | undefined>) {
  const input = parts.map((part) => String(part ?? "")).join("||");
  let hash = 2166136261;
  for (let idx = 0; idx < input.length; idx += 1) {
    hash ^= input.charCodeAt(idx);
    hash = Math.imul(hash, 16777619);
  }
  return `ui-${(hash >>> 0).toString(36)}`;
}

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value));
}

function summarizeEvents(events: FigPulseEvent[]) {
  const summary: Record<string, number> = {};
  for (const event of events) {
    summary[`source:${event.source}`] =
      (summary[`source:${event.source}`] ?? 0) + 1;
    summary[`stage:${event.stage}`] =
      (summary[`stage:${event.stage}`] ?? 0) + 1;
  }
  return summary;
}

export function buildFigInteractionPulse({
  graphId,
  selectedNode,
  hoveredNode,
  overlayMode,
  topMode,
  activeDrawer,
  timelineStepIdx,
  queryExplain,
  pulseTrace,
}: BuildInteractionPulseParams): FigInteractionPulse | null {
  const backendLedger = queryExplain?.reason_source_ledger ?? null;
  const events: FigPulseEvent[] = [
    ...(backendLedger?.events ?? []),
    ...(pulseTrace?.events ?? []),
  ];

  const uiEvents: FigPulseEvent[] = [];
  const selectedNodeId = selectedNode?.node_id ?? null;
  const hoveredNodeId = hoveredNode?.node_id ?? null;

  if (selectedNodeId) {
    uiEvents.push({
      event_id: stablePulseId([
        graphId,
        "selection",
        selectedNodeId,
        overlayMode,
        topMode,
        activeDrawer,
        timelineStepIdx,
      ]),
      protocol: "pulse-v2",
      graph_id: graphId,
      query_hash: queryExplain?.vector_hash ?? null,
      node_id: selectedNodeId,
      hop: null,
      stage: "ui_selection",
      source: "fig:selected",
      strength: 1,
      contribution: 1,
      evidence: {
        overlay_mode: overlayMode,
        top_mode: topMode,
        active_drawer: activeDrawer,
      },
    });
  }

  if (hoveredNodeId && hoveredNodeId !== selectedNodeId) {
    uiEvents.push({
      event_id: stablePulseId([
        graphId,
        "hover",
        hoveredNodeId,
        overlayMode,
        topMode,
        activeDrawer,
        timelineStepIdx,
      ]),
      protocol: "pulse-v2",
      graph_id: graphId,
      query_hash: queryExplain?.vector_hash ?? null,
      node_id: hoveredNodeId,
      hop: null,
      stage: "ui_hover",
      source: "fig:hover",
      strength: 0.45,
      contribution: 0.45,
      evidence: {
        overlay_mode: overlayMode,
        top_mode: topMode,
      },
    });
  }

  if (overlayMode && overlayMode !== "none") {
    uiEvents.push({
      event_id: stablePulseId([
        graphId,
        "overlay",
        overlayMode,
        selectedNodeId,
        hoveredNodeId,
        topMode,
      ]),
      protocol: "pulse-v2",
      graph_id: graphId,
      query_hash: queryExplain?.vector_hash ?? null,
      node_id: selectedNodeId ?? hoveredNodeId ?? backendLedger?.node_id ?? `${graphId}:overlay`,
      hop: null,
      stage: "ui_overlay",
      source: `fig:overlay:${overlayMode}`,
      strength: overlayMode === "cognitive" ? 0.65 : 0.42,
      contribution: 0.25,
      evidence: {
        overlay_mode: overlayMode,
        top_mode: topMode,
      },
    });
  }

  if (topMode && topMode !== "explore") {
    uiEvents.push({
      event_id: stablePulseId([graphId, "top-mode", topMode, selectedNodeId, hoveredNodeId]),
      protocol: "pulse-v2",
      graph_id: graphId,
      query_hash: queryExplain?.vector_hash ?? null,
      node_id: selectedNodeId ?? hoveredNodeId ?? backendLedger?.node_id ?? `${graphId}:mode`,
      hop: null,
      stage: "ui_mode",
      source: `fig:top:${topMode}`,
      strength: topMode === "lineage" ? 0.5 : 0.35,
      contribution: 0.2,
      evidence: {
        top_mode: topMode,
      },
    });
  }

  if (activeDrawer) {
    uiEvents.push({
      event_id: stablePulseId([
        graphId,
        "drawer",
        activeDrawer,
        selectedNodeId,
        hoveredNodeId,
      ]),
      protocol: "pulse-v2",
      graph_id: graphId,
      query_hash: queryExplain?.vector_hash ?? null,
      node_id: selectedNodeId ?? hoveredNodeId ?? backendLedger?.node_id ?? `${graphId}:drawer`,
      hop: null,
      stage: "ui_drawer",
      source: `fig:drawer:${activeDrawer}`,
      strength: 0.25,
      contribution: 0.15,
      evidence: {
        active_drawer: activeDrawer,
      },
    });
  }

  if (timelineStepIdx != null) {
    uiEvents.push({
      event_id: stablePulseId([
        graphId,
        "timeline",
        timelineStepIdx,
        selectedNodeId,
        hoveredNodeId,
      ]),
      protocol: "pulse-v2",
      graph_id: graphId,
      query_hash: queryExplain?.vector_hash ?? null,
      node_id:
        selectedNodeId ?? hoveredNodeId ?? backendLedger?.node_id ?? `${graphId}:timeline`,
      hop: timelineStepIdx,
      stage: "ui_timeline",
      source: "fig:timeline",
      strength: 0.3,
      contribution: 0.15,
      evidence: {
        timeline_step_idx: timelineStepIdx,
      },
    });
  }

  const allEvents = [...events, ...uiEvents];
  if (allEvents.length === 0 && !backendLedger && !pulseTrace) {
    return null;
  }

  const activeLayers = new Set<string>([
    ...(backendLedger?.active_layers ?? []),
    ...(pulseTrace?.layer_summary ? Object.keys(pulseTrace.layer_summary) : []),
  ]);
  for (const event of uiEvents) {
    activeLayers.add(event.stage);
  }

  const strongestLayers = [
    ...(backendLedger?.strongest_layers ?? []),
    ...(pulseTrace?.layer_summary
      ? Object.entries(pulseTrace.layer_summary).map(([layer, contribution]) => ({
          layer,
          contribution,
        }))
      : []),
    ...(selectedNodeId
      ? [{ layer: "ui_selection", contribution: 1 }]
      : []),
  ]
    .sort((left, right) => {
      const leftValue = Number(left.contribution ?? 0);
      const rightValue = Number(right.contribution ?? 0);
      return rightValue - leftValue || String(left.layer ?? "").localeCompare(String(right.layer ?? ""));
    })
    .slice(0, 8);

  const uiConfidence = clamp01(
    Math.max(
      ...(uiEvents.map((event) => event.strength ?? 0)),
      backendLedger?.confidence ?? 0,
      pulseTrace ? 0.5 : 0,
    ),
  );

  return {
    protocol: "pulse-v2",
    trace_id: stablePulseId([
      graphId,
      selectedNodeId,
      hoveredNodeId,
      overlayMode ?? "none",
      topMode ?? "explore",
      activeDrawer ?? "none",
      timelineStepIdx ?? "timeline-none",
      queryExplain?.vector_hash ?? backendLedger?.trace_id ?? pulseTrace?.trace_id ?? "none",
    ]),
    node_id: selectedNodeId ?? hoveredNodeId ?? backendLedger?.node_id ?? `${graphId}:live`,
    confidence: uiConfidence,
    event_count: allEvents.length,
    active_layers: Array.from(activeLayers).sort(),
    strongest_layers: strongestLayers,
    source_summary: summarizeEvents(allEvents),
    why_glowing: {
      ...(backendLedger?.why_glowing ?? {}),
      ui_context: {
        graph_id: graphId,
        selected_node_id: selectedNodeId,
        hovered_node_id: hoveredNodeId,
        overlay_mode: overlayMode,
        top_mode: topMode,
        active_drawer: activeDrawer,
        timeline_step_idx: timelineStepIdx,
      },
      ui_events: summarizeEvents(uiEvents),
    },
    events: allEvents,
    ui_context: {
      graph_id: graphId,
      selected_node_id: selectedNodeId,
      hovered_node_id: hoveredNodeId,
      overlay_mode: overlayMode,
      top_mode: topMode,
      active_drawer: activeDrawer,
      timeline_step_idx: timelineStepIdx,
    },
  };
}
