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
  | "warm"
  | "historical"
  | "compressed"
  | "deduplicated"
  | "pruned"
  | "cold"
  | "deactivated"
  | "unknown";

export type FigNodeTemperature = "hot" | "warm" | "cold";

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
  temperature?: FigNodeTemperature;
};

export type FigNodeAnchor = {
  doc_type?: string | null;
  block_type?: string | null;
  page?: number | null;
  slide?: number | null;
  sheet?: string | null;
  section?: string | null;
  row_start?: number | null;
  row_end?: number | null;
  char_start?: number | null;
  char_end?: number | null;
};

export type FigNode = {
  node_id: string;
  kind: string;
  level: number;
  vector_hash: string;
  display: FigNodeDisplay;
  metrics?: FigNodeMetrics;
  anchor?: FigNodeAnchor;
  provenance?: {
    raw_id?: string;
    block_id?: string;
  };
  /** Whether this node is protected from cold pruning. */
  long_term?: boolean;
  /** Topic cluster assignment (null = not yet clustered). */
  cluster_id?: number | null;
  /** ISO datetime when this node was first created. Used for timeline step filtering. */
  created_at?: string | null;
  /** Cognitive type classification for neural constellation view (fact, event, procedure, etc.). */
  cognitive_type?: string | null;
  /** Galaxy ID - source document grouping for constellation visualization. */
  galaxy_id?: string | null;
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
  /** ISO datetime when this edge was created. Used for timeline step filtering. */
  created_at?: string | null;
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

export type FigLatestEventResponse = {
  graph_id: string;
  last_seq: number;
  last_kind: string | null;
  last_ts: string | null;
  snapshot_hash: string | null;
  event_count: number;
};

// ---------------------------------------------------------------------------
// Topology
// ---------------------------------------------------------------------------

/**
 * Backend-computed scorecard fields.
 *
 * Policy (plan §11): D/H/λ are backend-verification-only when available.
 * The backend embeds this only when a shared MetricsScorecard helper is
 * callable at surface-build time (API contract §3.3.4). When the backend
 * cannot compute it cheaply, it returns null and the frontend falls back
 * to client-computed values derived from the backend-authoritative node/edge
 * data — those are labelled "computed" in the UI to distinguish them from
 * backend-verified values.
 */
export type FigBackendScorecard = {
  density: number;
  entropy: number;
  spectral_radius: number;
};

export type FigTopology = {
  node_count: number;
  edge_count: number;
  edge_counts_by_kind: Record<string, number>;
  /** null = backend did not compute; frontend falls back to client-side derivation. */
  scorecard: FigBackendScorecard | null;
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

export type FigNeighborhoodExpansion = {
  seedNodeId: string;
  addedNodeCount: number;
  addedEdgeCount: number;
};
