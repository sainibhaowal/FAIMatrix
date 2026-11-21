import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiGetMock, apiPostMock, resolveGraphIdMock } = vi.hoisted(() => ({
  apiGetMock: vi.fn(),
  apiPostMock: vi.fn(),
  resolveGraphIdMock: vi.fn((value?: string) => value || "U:test"),
}));

vi.mock("@/lib/api-client", () => ({
  apiGet: apiGetMock,
  apiPost: apiPostMock,
  resolveGraphId: resolveGraphIdMock,
}));

import {
  fetchBenchmarks,
  fetchEngineStats,
  fetchEvolutionHistory,
  fetchGraphMetrics,
  fetchGraphsSoft,
  fetchHealth,
  fetchNodeDetail,
  fetchNodeProvenance,
  fetchNodeScan,
  fetchNodeSubgraph,
  fetchSubgraph,
  triggerEvolution,
  verifyGraphHash,
} from "@/lib/api";

describe("API wrapper contract", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiPostMock.mockReset();
    resolveGraphIdMock.mockClear();
  });

  it("builds health, graph, node, evolution, and verification calls", async () => {
    apiGetMock.mockResolvedValue({ ok: true });
    apiPostMock.mockResolvedValue({ cycle_id: "c", status: "queued" });

    await fetchHealth();
    await fetchGraphMetrics("U:graph");
    await fetchNodeScan("U:graph", 10);
    await fetchNodeDetail("U:graph", "node/1");
    await fetchNodeSubgraph("U:graph", "node/1", 3);
    await fetchNodeProvenance("U:graph", "node/1");
    await triggerEvolution("U:graph");
    await fetchEvolutionHistory("U:graph", 7);
    await verifyGraphHash("U:graph");
    await fetchEngineStats("U:graph");

    expect(apiGetMock).toHaveBeenNthCalledWith(1, "/health");
    expect(apiGetMock).toHaveBeenCalledWith("/graphs/U%3Agraph/metrics");
    expect(apiGetMock).toHaveBeenCalledWith("/graphs/U%3Agraph/nodes?limit=10");
    expect(apiGetMock).toHaveBeenCalledWith("/graphs/U%3Agraph/node/node%2F1");
    expect(apiGetMock).toHaveBeenCalledWith(
      "/graphs/U%3Agraph/subgraph/node%2F1?depth=3",
    );
    expect(apiGetMock).toHaveBeenCalledWith(
      "/graphs/U%3Agraph/node/node%2F1/provenance",
    );
    expect(apiPostMock).toHaveBeenCalledWith(
      "/graphs/U%3Agraph/evolution/trigger",
    );
    expect(apiGetMock).toHaveBeenCalledWith(
      "/graphs/U%3Agraph/evolution/history?limit=7",
    );
    expect(apiGetMock).toHaveBeenCalledWith("/graphs/U%3Agraph/hash");
    expect(apiGetMock).toHaveBeenCalledWith("/graphs/U%3Agraph/stats");
  });

  it("normalizes benchmark, snapshot, and graph-list responses", async () => {
    apiGetMock
      .mockResolvedValueOnce([{ timestamp: "a" }])
      .mockResolvedValueOnce({ points: [{ timestamp: "b" }] })
      .mockResolvedValueOnce({ unexpected: true })
      .mockResolvedValueOnce({ nodes: [{ id: 1 }], links: null })
      .mockResolvedValueOnce({ nodes: null, links: [{ id: 2 }] })
      .mockResolvedValueOnce({ items: [{ graph_id: "U:one", node_count: 2 }] });

    await expect(fetchBenchmarks()).resolves.toEqual([{ timestamp: "a" }]);
    await expect(fetchBenchmarks()).resolves.toEqual([{ timestamp: "b" }]);
    await expect(fetchBenchmarks()).resolves.toEqual([]);
    await expect(fetchSubgraph(undefined, 99)).resolves.toEqual({
      nodes: [{ id: 1 }],
      links: [],
    });
    await expect(fetchSubgraph()).resolves.toEqual({
      nodes: [],
      links: [{ id: 2 }],
    });
    await expect(fetchGraphsSoft()).resolves.toEqual([
      { id: "U:one", name: "U:one" },
    ]);
  });

  it("degrades graph discovery safely when the backend is unavailable", async () => {
    apiGetMock.mockRejectedValue(new Error("offline"));
    await expect(fetchGraphsSoft()).resolves.toEqual([]);
  });
});
