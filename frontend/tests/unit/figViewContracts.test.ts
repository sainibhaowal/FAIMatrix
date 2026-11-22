import { beforeEach, describe, expect, it, vi } from "vitest";

const { getSessionMock } = vi.hoisted(() => ({
  getSessionMock: vi.fn(),
}));

vi.mock("next-auth/react", () => ({
  getSession: getSessionMock,
}));

import {
  appendFigInteractionPulse,
  fetchGraphExplain,
  fetchGraphLatestEvent,
  fetchGraphNeighborhood,
  fetchGraphSurface,
} from "@/lib/figViewApi";
import {
  buildAdjacency,
  buildNodeIndex,
  computeDensity,
  computeEntropy,
  computeGraphDistance,
  computeScorecard,
  computeSpectralRadius,
  filterNodesBySearch,
  getBestEdgeToNeighbor,
  getChildIds,
  getEdgesBetween,
  getInheritanceEdges,
  getNeighborIds,
  getNextRelevantNode,
  getOppositionEdges,
  getParentIds,
  getPrevRelevantNode,
  getRelevantNeighborOrder,
} from "@/lib/figViewGraphTransform";
import {
  buildEffectiveModeText,
  formatModePair,
  getPersistHelper,
  getProfileHelper,
  resolveUiModePolicy,
} from "@/lib/profilePersistModes";
import {
  createInitialTimelineSyncState,
  deriveTimelineSyncStatus,
  mergeTimelineResponse,
  nextTimelineCursor,
  normalizeTimelineEvents,
  shouldRebaseTimeline,
} from "@/lib/figViewTimelineSync";
import type {
  FigEdge,
  FigNode,
  FigSurfaceResponse,
  FigTimelineEvent,
} from "@/types/figView";

const node = (id: string, title = id): FigNode => ({
  node_id: id,
  kind: "fact",
  level: 0,
  vector_hash: `hash-${id}`,
  display: { title, title_source: "anchor", state: "active" },
});

const edge = (
  id: string,
  src: string,
  dst: string,
  kind = "inheritance",
  weight = 1,
): FigEdge => ({
  edge_id: id,
  src_node_id: src,
  dst_node_id: dst,
  kind,
  weight,
  meta: null,
});

describe("FIG graph transforms", () => {
  const nodes = [node("a", "Alpha"), node("b", "Beta"), node("c", "Gamma")];
  const edges = [
    edge("ab", "a", "b", "inheritance", 0.5),
    edge("ab2", "a", "b", "opposition", 0.9),
    edge("bc", "b", "c", "opposition", 0.9),
    edge("ca", "c", "a", "other", 0.2),
    edge("aa", "a", "a", "inheritance", 2),
  ];

  it("builds indexes, adjacency, neighborhoods, and filtered edges", () => {
    const index = buildNodeIndex(nodes);
    const adjacency = buildAdjacency(edges);
    expect(index.get("a")).toEqual(nodes[0]);
    expect(getNeighborIds("a", adjacency).sort()).toEqual(["b", "c"]);
    expect(getParentIds("b", adjacency)).toEqual(["a", "a"]);
    expect(getChildIds("a", adjacency)).toEqual(["b", "b"]);
    expect(getEdgesBetween("a", adjacency)).toHaveLength(4);
    expect(
      getOppositionEdges("a", adjacency).map((item) => item.edge_id),
    ).toEqual(["ab2"]);
    expect(
      getInheritanceEdges("a", adjacency).map((item) => item.edge_id),
    ).toEqual(["ab", "aa"]);
    expect(getBestEdgeToNeighbor("a", "b", adjacency)?.edge_id).toBe("ab2");
    expect(getBestEdgeToNeighbor("a", "missing", adjacency)).toBeNull();
    expect(computeGraphDistance("a", "a", adjacency)).toBe(0);
    expect(computeGraphDistance("a", "c", adjacency)).toBe(1);
    expect(computeGraphDistance("a", "c", adjacency, 0)).toBeNull();
    expect(computeGraphDistance("a", "missing", adjacency)).toBeNull();
  });

  it("searches and orders relevant neighbors deterministically", () => {
    const index = buildNodeIndex(nodes);
    const adjacency = buildAdjacency(edges);
    const search = nodes.map((item) => ({
      node_id: item.node_id,
      title: item.display.title,
      kind: item.kind,
      state: item.display.state,
    }));
    expect(filterNodesBySearch(search, " ")).toEqual([]);
    expect(
      filterNodesBySearch(search, "alp").map((item) => item.node_id),
    ).toEqual(["a"]);
    expect(
      filterNodesBySearch(search, "b").map((item) => item.node_id),
    ).toEqual(["b"]);
    expect(
      filterNodesBySearch(search, "gam").map((item) => item.node_id),
    ).toEqual(["c"]);
    expect(getRelevantNeighborOrder("a", adjacency, index)).toEqual(["b", "c"]);
    expect(getNextRelevantNode("a", adjacency, index)).toBe("b");
    expect(getPrevRelevantNode("missing", "a", adjacency, index)).toBe("c");
    expect(getPrevRelevantNode("c", "a", adjacency, index)).toBe("b");
  });

  it("computes scorecard metrics including empty graph guards", () => {
    expect(computeDensity(0, 0)).toBe(0);
    expect(computeDensity(1, 1)).toBe(0);
    expect(computeDensity(3, 3)).toBe(0.5);
    expect(computeEntropy([])).toBe(0);
    expect(computeEntropy([edge("1", "a", "b", "same")])).toBe(0);
    expect(
      computeEntropy([edge("1", "a", "b", "one"), edge("2", "b", "c", "two")]),
    ).toBe(1);
    expect(computeSpectralRadius([], [])).toBe(0);
    expect(computeSpectralRadius([node("a")], [])).toBe(0);
    expect(computeSpectralRadius(nodes, edges)).toBeGreaterThan(0);
    const scorecard = computeScorecard(nodes, edges);
    expect(scorecard.density).toBeGreaterThan(0);
    expect(scorecard.entropy).toBeGreaterThan(0);
  });
});

describe("FIG timeline and mode policy", () => {
  it("normalizes and merges timeline events without skipping cursors", () => {
    const event = (seq: number): FigTimelineEvent => ({
      seq,
      kind: "write",
      ts: null,
      payload_keys: [],
      graph_id: "U:g",
    });
    expect(createInitialTimelineSyncState()).toMatchObject({
      enabled: false,
      status: "idle",
    });
    expect(createInitialTimelineSyncState(true).enabled).toBe(true);
    expect(
      normalizeTimelineEvents([event(2), event(1), event(2), event(0)], 0).map(
        (item) => item.seq,
      ),
    ).toEqual([1, 2]);
    const current = {
      timeline: {
        after_seq: 0,
        next_seq: 2,
        has_more: false,
        events: [event(1), event(2)],
      },
    } as unknown as FigSurfaceResponse;
    const incoming = {
      timeline: {
        after_seq: 2,
        next_seq: 4,
        has_more: true,
        events: [event(2), event(3), event(4)],
      },
    } as unknown as FigSurfaceResponse;
    const merged = mergeTimelineResponse(current, incoming, 2);
    expect(merged.timeline?.events.map((item) => item.seq)).toEqual([
      1, 2, 3, 4,
    ]);
    expect(merged.timeline?.after_seq).toBe(0);
    expect(merged.timeline?.next_seq).toBe(4);
    expect(
      mergeTimelineResponse(
        current,
        { timeline: null } as unknown as FigSurfaceResponse,
        2,
      ).timeline,
    ).toBe(current.timeline);
    expect(deriveTimelineSyncStatus(false, true, false, false)).toBe("idle");
    expect(deriveTimelineSyncStatus(true, false, false, false)).toBe("idle");
    expect(deriveTimelineSyncStatus(true, true, true, false)).toBe(
      "catching_up",
    );
    expect(deriveTimelineSyncStatus(true, true, false, true)).toBe(
      "disconnected",
    );
    expect(deriveTimelineSyncStatus(true, true, false, false)).toBe("live");
    expect(nextTimelineCursor(2, 10, 5)).toBe(5);
    expect(nextTimelineCursor(6, 10, undefined)).toBe(6);
    expect(shouldRebaseTimeline(null, "b", 1, 2)).toBe(false);
    expect(shouldRebaseTimeline("a", "b", 1, 2)).toBe(true);
    expect(shouldRebaseTimeline("a", "a", 1, 3)).toBe(true);
    expect(shouldRebaseTimeline("a", "a", 1, 2)).toBe(false);
  });

  it("validates profile/persistence combinations and explanatory text", () => {
    expect(formatModePair(" FAST ", "RELAXED")).toBe("fast/relaxed");
    expect(formatModePair("invalid", "strict")).toBe("-");
    expect(getProfileHelper("fast")).toContain("Fast");
    expect(getProfileHelper("invalid")).toBe("Unknown profile.");
    expect(getPersistHelper("strict")).toContain("Persist strict");
    expect(getPersistHelper("invalid")).toBe("Unknown persist mode.");
    expect(resolveUiModePolicy("ingest", "fast", "strict").supported).toBe(
      true,
    );
    expect(resolveUiModePolicy("evolve", "unknown", "strict").supported).toBe(
      false,
    );
    expect(resolveUiModePolicy("evolve", "fast", "unknown").supported).toBe(
      false,
    );
    expect(
      buildEffectiveModeText("fast", "strict", "balanced", "relaxed", "wal"),
    ).toContain("Requested fast/strict -> Effective balanced/relaxed");
    expect(buildEffectiveModeText(null, null, null, null, null)).toContain(
      "durability: -",
    );
  });
});

describe("FIG API auth and request contracts", () => {
  beforeEach(() => {
    getSessionMock.mockReset();
    getSessionMock.mockResolvedValue({
      accessToken: "token",
      tenantId: "tenant",
    });
    vi.restoreAllMocks();
  });

  it("sends auth, encoded query options, and parses successful responses", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async () =>
        new Response(JSON.stringify({ ok: true }), {
          headers: { "content-type": "application/json" },
        }),
    );
    await fetchGraphSurface("U:graph", {
      nodeLimit: 3,
      edgeLimit: 4,
      timelineLimit: 5,
      afterSeq: 6,
      includeTopology: true,
    });
    await fetchGraphLatestEvent("U:graph");
    await fetchGraphNeighborhood("U:graph", "node/1", {
      depth: 2,
      nodeLimit: 3,
      edgeLimit: 4,
      edgeKinds: "inheritance",
    });
    await fetchGraphExplain("U:graph", "a", "b", {
      maxHops: 3,
      maxPaths: 2,
      edgeKinds: ["inheritance"],
    });
    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      cache: "no-store",
      headers: { Authorization: "Bearer token", "X-Tenant-Id": "tenant" },
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "include_topology=true",
    );
    expect(String(fetchMock.mock.calls[2]?.[0])).toContain("node_id=node%2F1");
    expect(
      JSON.parse(String(fetchMock.mock.calls[3]?.[1]?.body)),
    ).toMatchObject({
      from_node_id: "a",
      max_hops: 3,
    });
  });

  it("returns null for invalid pulse input and surfaces structured errors", async () => {
    expect(await appendFigInteractionPulse("", {} as never)).toBeNull();
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: "denied" }), { status: 403 }),
      );
    await expect(fetchGraphLatestEvent("U:g")).rejects.toThrow("denied");
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
