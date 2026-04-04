/**
 * FIG View types — matches backend graph API contract.
 *
 * Source of truth: frontend/Docs/03_Phase1_FIG_Graph_API_Contract.md
 * Backend: faim_native/api/routers/graph.py + faim_native/api/fig_graph_core.py
 */

// ---------------------------------------------------------------------------
// Snapshot
// ---------------------------------------------------------------------------

export type FigSnapshot = {
  graph_id: string;
  graph_version: number;
  graph_hash: string;
  as_of: string;
  consistent_read: boolean;
};

// ---------------------------------------------------------------------------
// Node
// ---------------------------------------------------------------------------

export type FigNodeDisplayState =
  | "active"
  | "historical"
  | "compressed"
  | "deduplicated"
  | "pruned"
  | "cold"
  | "deactivated"
  | "unknown";

export type FigNodeTitleSource =
  | "anchor"
  | "block_id"
  | "raw_id"
  | "vector_hash"
  | "node_id"
  | "unknown";

export type FigNodeDisplay = {
  title: string;
  title_source: FigNodeTitleSource;
  state: FigNodeDisplayState;
};

export type FigNodeMetrics = {
  touch_count: number;
  residual: number;
  last_access: string | null;
};

export type FigNode = {
  node_id: string;
  kind: string;
  level: number;
  vector_hash: string;
  display: FigNodeDisplay;
  metrics?: FigNodeMetrics;
  provenance?: {
    raw_id?: string;
    block_id?: string;
  };
};

// ---------------------------------------------------------------------------
// Edge
// ---------------------------------------------------------------------------

export type FigEdge = {
  edge_id: string;
  src_node_id: string;
  dst_node_id: string;
  kind: string;
  weight: number;
  meta: Record<string, unknown> | null;
};

// ---------------------------------------------------------------------------
// Timeline
// ---------------------------------------------------------------------------

export type FigTimelineEvent = {
  seq: number;
  kind: string;
  ts: string | null;
  payload_keys: string[];
  graph_id: string;
};

export type FigTimeline = {
  after_seq: number;
  next_seq: number;
  has_more: boolean;
  events: FigTimelineEvent[];
};

// ---------------------------------------------------------------------------
// Topology
// ---------------------------------------------------------------------------

export type FigTopology = {
  node_count: number;
  edge_count: number;
  edge_counts_by_kind: Record<string, number>;
  scorecard: null;
};

// ---------------------------------------------------------------------------
// API Responses
// ---------------------------------------------------------------------------

export type FigSurfaceResponse = {
  snapshot: FigSnapshot;
  nodes: FigNode[];
  edges: FigEdge[];
  timeline: FigTimeline | null;
  topology: FigTopology | null;
  controls: {
    similarity: {
      mode: string;
      notes: string;
    };
  };
  truncated: boolean;
  truncation_reason: string | null;
};

export type FigNeighborhoodResponse = {
  snapshot: FigSnapshot;
  seed_node_id: string;
  depth_requested: number;
  depth_effective: number;
  nodes: FigNode[];
  edges: FigEdge[];
  distances: Record<string, number>;
  truncated: boolean;
  truncation_reason: string | null;
};

export type FigExplainResponse = {
  snapshot: FigSnapshot;
  from_node_id: string;
  to_node_id: string;
  path_found: boolean;
  paths: Array<{
    node_ids: string[];
    edges: FigEdge[];
  }>;
  explanation: {
    summary: string;
    hops: number;
    edge_kinds_used: string[];
    relation_distance: number | null;
  };
};

// ---------------------------------------------------------------------------
// UI State
// ---------------------------------------------------------------------------

export type FigLoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "loaded"; data: FigSurfaceResponse }
  | { status: "empty"; snapshot: FigSnapshot }
  | { status: "error"; message: string }
  | { status: "degraded"; data: FigSurfaceResponse; warnings: string[] };
