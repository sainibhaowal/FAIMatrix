// src/lib/api.ts
import { apiGet, apiPost, resolveGraphId } from "@/lib/api-client";
export * from "@/lib/api-client";
import {
  GraphMetrics,
  BenchmarkPoint,
  GraphSubgraph,
  NodeScanItem,
  FaimNodeDetail,
  HealthStatus,
  UsedNodeSummary,
  GraphSummary,
} from "@/types/api";
export * from "@/types/api";

export function fetchHealth(): Promise<HealthStatus> {
  return apiGet<HealthStatus>("/health");
}

export function fetchGraphMetrics(graphId?: string): Promise<GraphMetrics> {
  const gid = resolveGraphId(graphId);
  return apiGet<GraphMetrics>(`/graphs/${encodeURIComponent(gid)}/metrics`);
}

export function fetchBenchmarks(graphId?: string): Promise<BenchmarkPoint[]> {
  const gid = resolveGraphId(graphId);
  return apiGet<
    BenchmarkPoint[] | { points?: BenchmarkPoint[]; graph_id?: string }
  >(`/benchmarks/${encodeURIComponent(gid)}/series?limit=200`).then((res) => {
    if (Array.isArray(res)) return res;
    if (res && Array.isArray(res.points)) return res.points;
    return [];
  });
}

export function fetchSubgraph(
  graphId?: string,
  limit = 250,
): Promise<GraphSubgraph> {
  const gid = resolveGraphId(graphId);
  return apiGet<{ nodes: any[]; links: any[] }>(
    `/graphs/${encodeURIComponent(gid)}/snapshot`,
  ).then((res) => ({
    nodes: res.nodes || [],
    links: res.links || [],
  }));
}

export function fetchNodeScan(
  graphId?: string,
  limit = 250,
): Promise<NodeScanItem[]> {
  const gid = resolveGraphId(graphId);
  return apiGet<NodeScanItem[]>(
    `/graphs/${encodeURIComponent(gid)}/nodes?limit=${limit}`,
  );
}

export function fetchNodeDetail(
  graphId: string,
  nodeId: string,
): Promise<FaimNodeDetail> {
  const gid = resolveGraphId(graphId);
  return apiGet<FaimNodeDetail>(
    `/graphs/${encodeURIComponent(gid)}/node/${encodeURIComponent(nodeId)}`,
  );
}

export function fetchNodeSubgraph(
  graphId: string | undefined,
  nodeId: string,
  depth = 2,
): Promise<GraphSubgraph> {
  const gid = resolveGraphId(graphId);
  return apiGet<GraphSubgraph>(
    `/graphs/${encodeURIComponent(gid)}/subgraph/${encodeURIComponent(nodeId)}?depth=${depth}`,
  );
}

export async function fetchGraphsSoft(): Promise<GraphSummary[]> {
  // Backend has no /graphs list endpoint — rely on universe resolution fallback
  // in TopBar instead. Returning empty avoids a noisy 404 in the console.
  return [];
}

// =============================================================================
// FAIM-Native API Functions
// =============================================================================

/**
 * Fetch full FAIMVector provenance for a node.
 * Returns: vector_hash, v_native, anchor, parents, fractions, residual, opp_signature, provenance
 */
export function fetchNodeProvenance(
  graphId: string,
  nodeId: string,
): Promise<any> {
  const gid = resolveGraphId(graphId);
  return apiGet<any>(
    `/graphs/${encodeURIComponent(gid)}/node/${encodeURIComponent(nodeId)}/provenance`,
  );
}

/**
 * Trigger an evolution cycle (pruning, merging, synthesis).
 */
export function triggerEvolution(
  graphId: string,
): Promise<{ cycle_id: string; status: string }> {
  const gid = resolveGraphId(graphId);
  return apiPost<{ cycle_id: string; status: string }>(
    `/graphs/${encodeURIComponent(gid)}/evolution/trigger`,
  );
}

/**
 * Fetch evolution history for a graph.
 */
export function fetchEvolutionHistory(
  graphId: string,
  limit = 50,
): Promise<any[]> {
  const gid = resolveGraphId(graphId);
  return apiGet<any[]>(
    `/graphs/${encodeURIComponent(gid)}/evolution/history?limit=${limit}`,
  );
}

/**
 * Verify graph hash for determinism proof.
 */
export function verifyGraphHash(
  graphId: string,
): Promise<{ graph_hash: string; node_count: number; edge_count: number }> {
  const gid = resolveGraphId(graphId);
  return apiGet<{ graph_hash: string; node_count: number; edge_count: number }>(
    `/graphs/${encodeURIComponent(gid)}/hash`,
  );
}

/**
 * Fetch engine statistics (nodes, edges, compression ratio, avg level).
 */
export function fetchEngineStats(graphId?: string): Promise<{
  total_nodes: number;
  total_edges: number;
  compression_ratio: number;
  redundancy: number;
  avg_level: number;
  graph_hash: string;
}> {
  const gid = resolveGraphId(graphId);
  return apiGet<any>(`/graphs/${encodeURIComponent(gid)}/stats`);
}
