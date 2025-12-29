// src/lib/api.ts
"use client";

/* ========================================================================== */
/*  FAIM Frontend API Client (Production-safe)                                 */
/*  - NO hardcoded demo IDs                                                    */
/*  - User identity: stable per-browser fallback (UUID) if auth not wired yet  */
/*  - Graph identity: MUST be the user Universe "U:..." (resolved via SSE)     */
/*      • We do NOT default to "MAIN" / "RAVIN_MAIN"                           */
/*      • We try localStorage keys set by the SSE contract handler             */
/* ========================================================================== */

/* =============================== Config =================================== */

export const API_BASE_URL =
  (process.env.NEXT_PUBLIC_FAIM_API_BASE_URL || "/api/v1").replace(/\/+$/, "");

/**
 * DO NOT use MAIN in production. Keep export for compatibility with existing imports,
 * but resolveGraphId() will refuse empty/invalid IDs.
 *
 * If you truly need an entry slug concept, keep it UX-only and map it server-side.
 */
export const DEFAULT_GRAPH_ID = (process.env.NEXT_PUBLIC_FAIM_DEFAULT_GRAPH_ID || "").trim();

/* =========================== Identity (User) ============================== */

function _stableBrowserId(storageKey: string): string {
  if (typeof window === "undefined") return "";
  const prev = window.localStorage.getItem(storageKey);
  if (prev && prev.trim()) return prev.trim();

  // Crypto-safe UUID in modern browsers
  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `u_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`;

  window.localStorage.setItem(storageKey, id);
  return id;
}

/**
 * Production intent:
 * - If NextAuth (or your auth) provides a real user id, store it in localStorage
 *   as "faim_user_id" and this will use it.
 * - Otherwise we generate a stable per-browser UUID (NOT "demo_user_123").
 */
export function getFaimUserId(): string {
  // Browser: prefer stored real id (set by auth layer)
  if (typeof window !== "undefined") {
    const v = window.localStorage.getItem("faim_user_id");
    if (v && v.trim()) return v.trim();
    return _stableBrowserId("faim_anon_user_id");
  }

  // Server: allow env injection (optional). Never default to demo.
  const env = (process.env.NEXT_PUBLIC_FAIM_USER_ID || "").trim();
  return env;
}

export function getFaimApiKey(): string {
  if (typeof window === "undefined") return "";
  try {
    const v = window.localStorage.getItem("faim_api_key");
    return v && v.trim() ? v.trim() : "";
  } catch {
    return "";
  }
}

export function buildFaimHeaders(extra?: Record<string, string>): Record<string, string> {
  const uid = getFaimUserId();
  const apiKey = getFaimApiKey();
  return {
    ...(uid ? { "X-FAIM-USER": uid } : {}),
    ...(apiKey ? { "X-FAIM-KEY": apiKey } : {}),
    ...(extra || {}),
  };
}

/* =========================== Identity (Graph) ============================= */

/**
 * In production, the only correct graphId for a user session is the Universe id "U:...."
 * which comes from the SSE `contract.universe.graph_id`.
 *
 * Your SSE onContract handler should set:
 *   localStorage.setItem("faim_universe_graph_id", contract.universe.graph_id)
 */
export function getUniverseGraphId(): string {
  if (typeof window === "undefined") return "";

  // ✅ UI uses this key (dot) — treat it as canonical
  const dot = window.localStorage.getItem("faim.universe_graph_id");
  if (dot && dot.trim()) return dot.trim();

  // ✅ Also support underscore key (older/newer variants)
  const a = window.localStorage.getItem("faim_universe_graph_id");
  if (a && a.trim()) return a.trim();

  // Backward-compatible fallback keys (if you used different names earlier)
  const b = window.localStorage.getItem("faim_graph_id");
  if (b && b.trim()) return b.trim();

  const c = window.localStorage.getItem("faim_entry_graph_id");
  if (c && c.trim()) return c.trim();

  return "";
}

function resolveGraphId(input?: string): string {
  const raw = (input ?? "").trim();
  const fromStorage = getUniverseGraphId();

  const gid = raw || fromStorage;

  // Enforce production universe format. If you later support multiple graphs,
  // extend this predicate (but do not reintroduce demo slugs).
  if (!gid) {
    throw new Error(
      "FAIM graph_id is not resolved yet. Expected Universe id from SSE contract. " +
      "Ensure SSE onContract stores localStorage key 'faim_universe_graph_id'."
    );
  }

  // Strong guard: Universe IDs are always U:...
  if (!gid.startsWith("U:")) {
    throw new Error(
      `Invalid graph_id '${gid}'. Production requires Universe id like 'U:xxxx'.`
    );
  }

  return gid;
}

/* ================================ Types =================================== */

/**
 * Your backend /health appears to be: {status:"ok", version?:string}
 * Keep version optional to avoid crashing UI.
 */
export type HealthStatus = {
  status: "ok" | "degraded" | "down";
  version?: string;
  mode?: string;
  gpu?: {
    enabled?: boolean;
    available?: boolean;
    device?: string;
    mem_free_bytes?: number | null;
    mem_total_bytes?: number | null;
  };
};

/**
 * Matches your backend metrics payload (observed):
 * {"node_count":3,"edge_count":3,"compression_ratio":1.0,"redundancy":0.0,"drift":0.0,"retrieve_p50_ms":0.0,"retrieve_p95_ms":0.0}
 */
export type GraphMetrics = {
  node_count: number;
  edge_count: number;
  compression_ratio: number;
  redundancy: number;
  drift: number;
  retrieve_p50_ms: number;
  retrieve_p95_ms: number;
  // optional extras if backend later adds
  graph_id?: string;
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
  latency: {
    retrieve_p50_ms: number;
    retrieve_p95_ms: number;
  };
};

export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

export type UsedNodeSummary = {
  node_id: string;
  score: number;
  snippet?: string;
};

export type FaimNodeDetail = {
  node_id: string;
  payload_preview?: string;
  created_at?: string;
  last_accessed_at?: string;
  inheritance?: Array<{ parent_id: string; weight: number }>;
  merges?: Array<{ from_id: string; at: string }>;
  metrics?: { redundancy?: number; drift?: number };
};

export type GraphNode = {
  id: string;
  label?: string;
  group?: string;
};

export type GraphLink = {
  source: string;
  target: string;
  weight?: number;
};

export type GraphSubgraph = {
  nodes: GraphNode[];
  links: GraphLink[];
};

export type NodeScanItem = {
  id: string;
  degree?: number | null;
};

/* =========================== Internal helpers ============================= */

function _mkUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${p}`;
}

import { getSession } from "next-auth/react";

async function apiGet<T>(path: string): Promise<T> {
  const url = _mkUrl(path);

  // Auth injection (Phase 1)
  const session = await getSession();
  const extraHeaders: Record<string, string> = {};
  if (session && (session as any).accessToken) {
    extraHeaders["Authorization"] = `Bearer ${(session as any).accessToken}`;
  }

  const res = await fetch(url, {
    cache: "no-store",
    headers: buildFaimHeaders(extraHeaders),
  });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost<T = void>(path: string, body?: unknown): Promise<T> {
  const url = _mkUrl(path);

  // Auth injection (Phase 1)
  const session = await getSession();
  const extraHeaders: Record<string, string> = { "Content-Type": "application/json" };
  if (session && (session as any).accessToken) {
    extraHeaders["Authorization"] = `Bearer ${(session as any).accessToken}`;
  }

  const res = await fetch(url, {
    method: "POST",
    headers: buildFaimHeaders(extraHeaders),
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return (res.status === 204 ? (undefined as T) : res.json());
}

/* ============================== Public API ================================ */

export function fetchHealth(): Promise<HealthStatus> {
  return apiGet<HealthStatus>("/health");
}

/**
 * If graphId is omitted, we resolve from localStorage (Universe id).
 * This prevents URLs like /graphs/metrics (missing graph id).
 */
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

export function fetchSubgraph(graphId?: string, limit = 250): Promise<GraphSubgraph> {
  const gid = resolveGraphId(graphId);
  // Backend uses /snapshot for full graph data, not /subgraph (which requires node_id)
  return apiGet<{ nodes: any[]; links: any[] }>(
    `/graphs/${encodeURIComponent(gid)}/snapshot`
  ).then((res) => ({
    nodes: res.nodes || [],
    links: res.links || [],
  }));
}

export function fetchNodeScan(graphId?: string, limit = 250): Promise<NodeScanItem[]> {
  const gid = resolveGraphId(graphId);
  return apiGet<NodeScanItem[]>(
    `/graphs/${encodeURIComponent(gid)}/nodes?limit=${limit}`
  );
}

export function fetchNodeSubgraph(
  graphId: string | undefined,
  nodeId: string,
  depth = 2
): Promise<GraphSubgraph> {
  const gid = resolveGraphId(graphId);
  return apiGet<GraphSubgraph>(
    `/graphs/${encodeURIComponent(gid)}/subgraph/${encodeURIComponent(nodeId)}?depth=${depth}`
  );
}

export function fetchNodeDetail(graphId: string, nodeId: string): Promise<FaimNodeDetail> {
  const gid = resolveGraphId(graphId);
  return apiGet<FaimNodeDetail>(
    `/graphs/${encodeURIComponent(gid)}/node/${encodeURIComponent(nodeId)}`
  );
}

export function postChat(
  message: string,
  graphId?: string
): Promise<{ reply: string; used_nodes: UsedNodeSummary[] }> {
  const gid = resolveGraphId(graphId);
  return apiPost("/chat", { graph_id: gid, message });
}

export function triggerEvolve(graphId?: string): Promise<void> {
  const gid = resolveGraphId(graphId);
  return apiPost<void>(`/graphs/${encodeURIComponent(gid)}/evolve`);
}

export function triggerRetention(): Promise<void> {
  return apiPost<void>("/admin/retention/run");
}
