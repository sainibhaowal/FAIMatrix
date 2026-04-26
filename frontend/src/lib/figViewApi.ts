/**
 * FIG View API client — fetch functions for graph surface, neighborhood, explain.
 *
 * Auth pattern: same as evolution page (getSession → Bearer token).
 * Routing: proxied through Next.js rewrites (/api/v1/* → backend).
 */

import { getSession } from "next-auth/react";

import type {
  FigExplainResponse,
  FigLatestEventResponse,
  FigNeighborhoodResponse,
  FigSurfaceResponse,
} from "@/types/figView";

// ---------------------------------------------------------------------------
// Auth helpers (same pattern as evolution page)
// ---------------------------------------------------------------------------

async function figAuthHeaders(): Promise<Record<string, string>> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const tenantId = (session as { tenantId?: string } | null)?.tenantId;
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (tenantId) headers["X-Tenant-Id"] = tenantId;
  return headers;
}

async function figRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await figAuthHeaders();
  const merged: Record<string, string> = {
    ...headers,
    ...(init?.headers as Record<string, string> | undefined),
  };

  const response = await fetch(path, {
    ...init,
    headers: merged,
    cache: "no-store",
  });

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    const msg =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Request failed (${response.status})`;
    throw new Error(msg);
  }

  return (payload ?? {}) as T;
}

// ---------------------------------------------------------------------------
// Graph Surface
// ---------------------------------------------------------------------------

export type SurfaceOpts = {
  nodeLimit?: number;
  edgeLimit?: number;
  timelineLimit?: number;
  afterSeq?: number;
  includeTopology?: boolean;
};

export async function fetchGraphSurface(
  graphId: string,
  opts: SurfaceOpts = {},
): Promise<FigSurfaceResponse> {
  const params = new URLSearchParams({ graph_id: graphId });
  if (opts.nodeLimit != null) params.set("node_limit", String(opts.nodeLimit));
  if (opts.edgeLimit != null) params.set("edge_limit", String(opts.edgeLimit));
  if (opts.timelineLimit != null)
    params.set("timeline_limit", String(opts.timelineLimit));
  if (opts.afterSeq != null) params.set("after_seq", String(opts.afterSeq));
  if (opts.includeTopology != null)
    params.set("include_topology", String(opts.includeTopology));

  return figRequest<FigSurfaceResponse>(`/api/v1/graph/surface?${params}`);
}

// ---------------------------------------------------------------------------
// Graph Latest Event
// ---------------------------------------------------------------------------

export async function fetchGraphLatestEvent(
  graphId: string,
): Promise<FigLatestEventResponse> {
  const params = new URLSearchParams({ graph_id: graphId });
  return figRequest<FigLatestEventResponse>(`/api/v1/events/latest?${params}`);
}

// ---------------------------------------------------------------------------
// Graph Neighborhood
// ---------------------------------------------------------------------------

export type NeighborhoodOpts = {
  depth?: number;
  nodeLimit?: number;
  edgeLimit?: number;
  edgeKinds?: string;
};

export async function fetchGraphNeighborhood(
  graphId: string,
  nodeId: string,
  opts: NeighborhoodOpts = {},
): Promise<FigNeighborhoodResponse> {
  const params = new URLSearchParams({ graph_id: graphId, node_id: nodeId });
  if (opts.depth != null) params.set("depth", String(opts.depth));
  if (opts.nodeLimit != null) params.set("node_limit", String(opts.nodeLimit));
  if (opts.edgeLimit != null) params.set("edge_limit", String(opts.edgeLimit));
  if (opts.edgeKinds != null) params.set("edge_kinds", opts.edgeKinds);

  return figRequest<FigNeighborhoodResponse>(
    `/api/v1/graph/neighborhood?${params}`,
  );
}

// ---------------------------------------------------------------------------
// Graph Path Explain
// ---------------------------------------------------------------------------

export type ExplainOpts = {
  maxHops?: number;
  maxPaths?: number;
  edgeKinds?: string[];
};

export async function fetchGraphExplain(
  graphId: string,
  fromNodeId: string,
  toNodeId: string,
  opts: ExplainOpts = {},
): Promise<FigExplainResponse> {
  const params = new URLSearchParams({ graph_id: graphId });
  return figRequest<FigExplainResponse>(
    `/api/v1/graph/paths/explain?${params}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from_node_id: fromNodeId,
        to_node_id: toNodeId,
        ...(opts.maxHops != null ? { max_hops: opts.maxHops } : {}),
        ...(opts.maxPaths != null ? { max_paths: opts.maxPaths } : {}),
        ...(opts.edgeKinds ? { edge_kinds: opts.edgeKinds } : {}),
      }),
    },
  );
}
