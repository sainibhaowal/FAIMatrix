// src/lib/api.ts
import { apiGet, apiPost, resolveGraphId } from "@/lib/api-client";
export * from "@/lib/api-client";
import { GraphMetrics, BenchmarkPoint, GraphSubgraph, NodeScanItem, FaimNodeDetail, HealthStatus, UsedNodeSummary, GraphSummary } from "@/types/api";
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
  try {
    const data = await apiGet<GraphSummary[]>("/graphs");
    if (Array.isArray(data)) return data;
    return [];
  } catch {
    return [];
  }
}
