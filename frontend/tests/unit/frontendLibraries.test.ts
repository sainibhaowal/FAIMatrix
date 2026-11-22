import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  apiGet,
  apiPost,
  buildFaimHeaders,
  getFaimApiKey,
  getFaimUserId,
  getUniverseGraphId,
  isRemoteApiBase,
  resolveGraphId,
} from "@/lib/api-client";
import {
  discoverEmbeddingModels,
  testEmbeddingProvider,
} from "@/lib/embeddingProviderDiscovery";
import {
  addEmbeddingProvider,
  getActiveEmbeddingProvider,
  loadEmbeddingProviders,
  normalizeBaseUrl,
  removeEmbeddingProvider,
  setActiveEmbeddingProvider,
  updateEmbeddingProvider,
} from "@/lib/embeddingProviders";
import {
  applyLayout,
  clampDraggedNode,
  createElasticGravityForce,
  edgeColorByKind,
  getLayoutConfig,
  nodeColorByCausality,
  nodeColorByEvolution,
  nodeColorByIdentity,
  nodeColorByLineageDepth,
  nodeColorByRetrieval,
  nodeColorByState,
  nodeColorByTemporal,
  nodeSizeByLevel,
  nodeSizeByRetrievalBoost,
} from "@/lib/figViewLayout";
import {
  clearStaleGraphState,
  loadGraphViewState,
  nodeStateClass,
  persistGraphViewState,
  safeNodeTitle,
} from "@/lib/figViewSafety";
import { normalizeApiErrorMessage } from "@/lib/errorMessages";
import { readJsonSafely } from "@/lib/safeFetch";

const response = (body: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    ...init,
  });

describe("frontend library contracts", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("normalizes API errors and safely reads JSON responses", async () => {
    expect(normalizeApiErrorMessage("  bad request  ")).toBe("  bad request  ");
    expect(normalizeApiErrorMessage(["one", { msg: "two" }, null])).toBe(
      "one, two",
    );
    expect(normalizeApiErrorMessage({ detail: { msg: "nested" } })).toBe(
      "nested",
    );
    expect(normalizeApiErrorMessage({ msg: "direct" })).toBe("direct");
    expect(normalizeApiErrorMessage({})).toBe("Request failed");

    expect(await readJsonSafely(response({ ok: true }))).toEqual({ ok: true });
    expect(
      await readJsonSafely(
        new Response("not-json", { headers: { "content-type": "text/plain" } }),
      ),
    ).toBeNull();
    expect(
      await readJsonSafely(
        new Response("{", { headers: { "content-type": "application/json" } }),
      ),
    ).toBeNull();
  });

  it("protects browser identity, graph resolution, and HTTP response handling", async () => {
    expect(isRemoteApiBase()).toBe(false);
    expect(getFaimApiKey()).toBeNull();
    expect(getUniverseGraphId()).toBeNull();
    expect(resolveGraphId("plain-id")).toBe("");
    localStorage.setItem("faim.universe_graph_id", "U:stored");
    expect(resolveGraphId()).toBe("U:stored");
    expect(resolveGraphId("U:provided")).toBe("U:provided");
    localStorage.setItem("faim_api_key", "secret");
    expect(getFaimApiKey()).toBe("secret");
    expect(getFaimUserId()).toBe(getFaimUserId());
    expect(buildFaimHeaders({ Accept: "application/json" })).toMatchObject({
      "Content-Type": "application/json",
      Accept: "application/json",
    });

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ value: 1 }))
      .mockResolvedValueOnce(response({ value: 2 }))
      .mockResolvedValueOnce(
        new Response("failure", { status: 503, statusText: "Unavailable" }),
      );
    await expect(apiGet<{ value: number }>("/health")).resolves.toEqual({
      value: 1,
    });
    await expect(
      apiPost<{ value: number }>("/write", { x: 1 }),
    ).resolves.toEqual({
      value: 2,
    });
    await expect(apiGet("/broken")).rejects.toThrow("API Error 503: failure");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ x: 1 }),
    });
  });

  it("provides safe embedding provider discovery and CRUD behavior", async () => {
    expect(normalizeBaseUrl(" https://example.test/ ")).toBe(
      "https://example.test/v1",
    );
    expect(normalizeBaseUrl("https://example.test/v1/")).toBe(
      "https://example.test/v1",
    );

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ models: ["a", 2], dimension: 3 }))
      .mockResolvedValueOnce(response({ message: "bad" }, { status: 400 }))
      .mockResolvedValueOnce(response({ models: [] }))
      .mockResolvedValueOnce(response({ success: true }))
      .mockRejectedValueOnce(new Error("offline"));
    await expect(
      discoverEmbeddingModels("https://provider.test", "key"),
    ).resolves.toEqual({
      models: ["a", "2"],
      dimension: 3,
    });
    await expect(
      discoverEmbeddingModels("https://provider.test"),
    ).rejects.toThrow("bad");
    await expect(
      discoverEmbeddingModels("https://provider.test"),
    ).rejects.toThrow("No models found from provider");
    await expect(
      testEmbeddingProvider({ baseUrl: "https://provider.test", model: "m" }),
    ).resolves.toBe(true);
    await expect(
      testEmbeddingProvider({ baseUrl: "https://provider.test" }),
    ).resolves.toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(5);

    const first = addEmbeddingProvider({
      name: "Local",
      type: "local",
      baseUrl: "http://localhost:9000",
      status: "untested",
      isActive: true,
    });
    const updated = addEmbeddingProvider({
      name: "local",
      type: "local",
      baseUrl: "http://localhost:9000/v1",
      status: "online",
      isActive: false,
    });
    expect(updated.id).toBe(first.id);
    expect(updated.status).toBe("online");
    expect(loadEmbeddingProviders()).toHaveLength(1);
    expect(updateEmbeddingProvider("missing", { status: "error" })).toBeNull();
    expect(updateEmbeddingProvider(first.id, { model: "m" })?.model).toBe("m");
    const second = addEmbeddingProvider({
      name: "Cloud",
      type: "openai",
      baseUrl: "https://cloud.test/v1",
      status: "online",
      isActive: true,
    });
    expect(getActiveEmbeddingProvider()?.id).toBe(second.id);
    setActiveEmbeddingProvider(first.id);
    expect(getActiveEmbeddingProvider()?.id).toBe(first.id);
    removeEmbeddingProvider(first.id);
    expect(getActiveEmbeddingProvider()?.id).toBe(second.id);
    removeEmbeddingProvider(second.id);
    expect(loadEmbeddingProviders()).toEqual([]);
    localStorage.setItem("faim.embeddingProviders", "not-json");
    expect(loadEmbeddingProviders()).toEqual([]);
  });

  it("persists FIG state without allowing stale or cross-graph state", () => {
    const node = {
      node_id: "abcdefghijk",
      kind: "fact",
      display: { title: "  Title  ", state: "active" },
    } as never;
    expect(safeNodeTitle(node)).toBe("Title");
    expect(nodeStateClass(node)).toBe("active");
    expect(safeNodeTitle({ node_id: "abcdefgh", kind: "fact" } as never)).toBe(
      "fact·abcdefgh",
    );
    expect(
      nodeStateClass({
        node_id: "x",
        kind: "fact",
        display: { state: "bad" },
      } as never),
    ).toBe("unknown");

    persistGraphViewState("U:one", 4, { tab: "graph" });
    persistGraphViewState("U:two", 4, { tab: "other" });
    expect(loadGraphViewState("U:one", 4)).toEqual({ tab: "graph" });
    expect(loadGraphViewState("U:one", 3)).toBeNull();
    expect(loadGraphViewState("U:missing", 4)).toBeNull();
    localStorage.setItem("faim.fig.view_state.U:bad", "{");
    expect(loadGraphViewState("U:bad", 1)).toBeNull();
    clearStaleGraphState("U:one");
    expect(localStorage.getItem("faim.fig.view_state.U:one")).not.toBeNull();
    expect(localStorage.getItem("faim.fig.view_state.U:two")).toBeNull();
  });

  it("covers deterministic FIG layout, color, size, and force safeguards", () => {
    expect(getLayoutConfig("explore").dagMode).toBeNull();
    expect(getLayoutConfig("analyze").chargeStrength).toBe(-100);
    expect(getLayoutConfig("lineage").dagMode).toBe("td");

    const force = createElasticGravityForce(1, 10) as ((
      alpha: number,
    ) => void) & {
      initialize: (nodes: any[]) => void;
    };
    const nodes = [
      { x: 20, y: 0, z: 0, vx: 0, vy: 0, vz: 0 },
      { x: 20, y: 0, z: 0, fx: 1, fy: 1, fz: 1 },
    ];
    force.initialize(nodes);
    force(1);
    expect(nodes[0].x).toBe(10);
    expect(nodes[0].vx).toBeLessThan(0);
    expect(nodes[1].x).toBe(20);
    const node: Record<string, number | undefined> = { x: 100, y: 0, z: 0 };
    clampDraggedNode(node, 5);
    expect(node.fx).toBe(5);
    clampDraggedNode(null);

    const charge = { strength: vi.fn(), distanceMax: vi.fn() };
    const link = { distance: vi.fn() };
    const graphNodes = [{ x: 1, y: 2, z: 3, fx: 4, fy: 5, fz: 6 }];
    const fg = {
      current: {
        d3Force: vi.fn((name: string) =>
          name === "charge" ? charge : name === "link" ? link : null,
        ),
        graphData: vi.fn(() => ({ nodes: graphNodes })),
        d3ReheatSimulation: vi.fn(),
      },
    };
    applyLayout(fg, getLayoutConfig("lineage"), undefined, false);
    expect(charge.strength).toHaveBeenCalledWith(-80);
    expect(link.distance).toHaveBeenCalledWith(60);
    expect(fg.current.d3ReheatSimulation).toHaveBeenCalled();
    expect(graphNodes[0].fx).toBeUndefined();

    expect(nodeColorByState("active", false)).toBe("#34d399");
    expect(nodeColorByState("unknown", true)).toBe("#22d3ee");
    expect(nodeColorByIdentity("same", false)).toBe(
      nodeColorByIdentity("same", false),
    );
    expect(nodeColorByIdentity("same", true)).toBe("#22d3ee");
    expect(nodeColorByLineageDepth(-1, false)).toBe("#f97316");
    expect(nodeColorByLineageDepth(99, false)).toBe("#a78bfa");
    expect(edgeColorByKind("inheritance")).toBe("#22d3ee");
    expect(edgeColorByKind("other")).toBe("#94a3b8");
    expect(nodeSizeByLevel(3)).toBe(6);
    expect(nodeSizeByLevel(1)).toBe(4);
    expect(nodeSizeByLevel(0)).toBe(2.5);
    expect(nodeColorByRetrieval(0.9, false)).toBe("#22d3ee");
    expect(nodeColorByRetrieval(0.3, false)).toBe("#164e63");
    expect(nodeColorByRetrieval(0, true)).toBe("#22d3ee");
    expect(nodeColorByEvolution("active", 0.9, false)).toBe("#34d399");
    expect(nodeColorByEvolution("cold", 1, false)).toBe("#334155");
    expect(nodeColorByEvolution("deduplicated", 0, false)).toBe("#a78bfa");
    expect(nodeColorByEvolution("active", 0, true)).toBe("#22d3ee");
    expect(nodeColorByTemporal(0.9, false)).toBe("#f97316");
    expect(nodeColorByTemporal(0, false)).toBe("#1e293b");
    expect(nodeSizeByRetrievalBoost(4, 2)).toBe(8);
    expect(nodeColorByCausality(0.9, false)).toBe("#ef4444");
    expect(nodeColorByCausality(0, false)).toBe("#1e293b");
  });
});
