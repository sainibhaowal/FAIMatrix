// src/shared/types/api.ts

export type GraphSummary = {
  id: string;
  name: string;
};

export type HealthStatus = {
  status: "ok" | "degraded" | "down";
  version?: string;
  gpu?: {
    enabled?: boolean;
    available?: boolean;
    device?: string;
    mem_free_bytes?: number;
    mem_total_bytes?: number;
  };
};

export type GraphMetrics = {
  graph_id: string;
  ts: number;
  nodes: number;
  node_count: number;
  links: number;
  link_count: number;
  cr: number;
  compression_ratio: number;
  redundancy: number;
  drift: number;
  raw_bytes?: number;
  faim_bytes?: number;
  latency?: {
    store_p50_ms?: number;
    retrieve_p50_ms?: number;
    retrieve_p95_ms?: number;
  };
};

export type BenchmarkPoint = {
  timestamp: string;
  nodes: number;
  cr: number;
  redundancy: number;
  drift: number;
  latency?: {
    store_p50_ms?: number;
    retrieve_p50_ms?: number;
    retrieve_p95_ms?: number;
  };
};

export type GraphNode = {
  id: string;
  label?: string;
  novelty?: number;
  evolution_flags?: string[];
  [key: string]: any;
};

export type GraphLink = {
  source: string;
  target: string;
  weight?: number;
  rel?: string;
  [key: string]: any;
};

export type GraphSubgraph = {
  nodes: GraphNode[];
  links: GraphLink[];
};

export type NodeScanItem = {
  id: string;
  label?: string;
  degree?: number;
  created_at?: string;
};

export type FaimNodeDetail = {
  id: string;
  label: string;
  payload: any;
  context_window?: string[];
  associations: Array<{ id: string; rel: string; weight: number }>;
};

export type UsedNodeSummary = { id: string; score?: number };
