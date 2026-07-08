import { describe, expect, it } from "vitest";

import { buildFigInteractionPulse } from "@/lib/figViewPulse";
import type { FigNode, FigPulseTrace, FigQueryExplain } from "@/types/figView";

const node = (node_id: string): FigNode =>
  ({
    node_id,
    kind: "fact",
    level: 1,
    vector_hash: "vh",
    display: { title: node_id, title_source: "node_id", state: "active" },
  }) as FigNode;

describe("buildFigInteractionPulse", () => {
  it("merges UI interaction state into a pulse-v2 ledger", () => {
    const queryExplain = {
      vector_hash: "query-hash",
      reason_source_ledger: {
        protocol: "pulse-v2",
        trace_id: "backend-trace",
        node_id: "node-a",
        confidence: 0.4,
        event_count: 2,
        active_layers: ["semantic_registry"],
        strongest_layers: [{ layer: "semantic_registry", contribution: 2 }],
        source_summary: { "source:backend": 2 },
        why_glowing: {
          expansion_sources: { conceptnet: 2 },
          graph_hops: [{ hop: 1, kind: "inheritance" }],
          reranker_components: { sim: 0.4 },
          late_interaction_components: { phrase: 0.1 },
          domain_memory: { node_scores: { "node-a": 0.7 }, query_links: [] },
          semantic_signature: { alias_families: 1 },
          candidate_pool: { total: 2 },
        },
        events: [],
      },
    } as FigQueryExplain;
    const pulseTrace = {
      protocol: "pulse-v2",
      trace_id: "trace",
      path_length: 1,
      source: "graph.paths.explain",
      layer_summary: { semantic_signature: 1 },
      steps: [],
      events: [],
    } as FigPulseTrace;

    const pulse = buildFigInteractionPulse({
      graphId: "graph-1",
      selectedNode: node("node-a"),
      hoveredNode: node("node-b"),
      overlayMode: "cognitive",
      topMode: "lineage",
      activeDrawer: "inspector",
      timelineStepIdx: 3,
      queryExplain,
      pulseTrace,
    });

    expect(pulse).not.toBeNull();
    expect(pulse?.protocol).toBe("pulse-v2");
    expect(pulse?.ui_context?.selected_node_id).toBe("node-a");
    expect(pulse?.ui_context?.hovered_node_id).toBe("node-b");
    expect(pulse?.source_summary["source:fig:selected"]).toBe(1);
    expect(pulse?.source_summary["stage:ui_overlay"]).toBe(1);
    expect(pulse?.active_layers).toContain("semantic_registry");
    expect(pulse?.active_layers).toContain("ui_selection");
    expect(pulse?.events.some((event) => event.stage === "ui_selection")).toBe(
      true,
    );
  });
});
