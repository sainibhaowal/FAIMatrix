// src/lib/realtime.ts
"use client";

/* ========================================================================== */
/*  FAIM Realtime (SSE via fetch)                                             */
/*  - Matches backend /api/v1/stream contract                                 */
/*  - Sends X-FAIM-USER via headers (EventSource cannot)                      */
/*  - IMPORTANT (Production): graph_id is OPTIONAL.                           */
/*      • If graph_id is omitted → backend resolves to user's Universe.       */
/*      • UI must treat the SSE "contract.universe.graph_id" as source truth. */
/*  - Provides BOTH: startFaimStream() (imperative) + useFaimStream() (hook)  */
/* ========================================================================== */

import { useEffect, useRef } from "react";
import { API_BASE_URL, buildFaimHeaders } from "@/lib/api";

/* ================================ Types =================================== */

export type StreamContract = {
  universe: { graph_id: string; label: string };
  galaxies: Array<{ id: string; label: string; size: number }>;
  policy: {
    graph_id_is_user_universe: boolean;
    frontend_never_prompts_for_graph_id: boolean;
    galaxies_are_clusters_not_graphs: boolean;
  };
};

export type FigDelta = {
  graph_id: string;
  ts: number;
  delta: {
    kind: string;
    nodes_added?: Array<{ id: string }>;
    links_added?: Array<{ source: string; target: string }>;
    nodes_removed?: Array<{ id: string }>;
    links_removed?: Array<{ source: string; target: string }>;
  };
};

export type ChatStoreEvent = {
  graph_id: string;
  trace_id: string;
  turn_id: string;
  created_node_ids: string[];
  created_fact_ids: string[];
  summary: string;
  ts: number;
};

export type ToastEvent = {
  graph_id: string;
  ts: number;
  level: "success" | "info" | "warning" | "error";
  message: string;
  code?: string;
};

export type MetricsEvent = {
  graph_id?: string;
  ts?: number;
  nodes?: number;
  cr?: number;
  redundancy?: number;
  drift?: number;
  latency?: {
    store_p50_ms?: number;
    retrieve_p50_ms?: number;
    retrieve_p95_ms?: number;
  };
};

export type BenchPoint = {
  timestamp: string;
  nodes: number;
  cr: number;
  redundancy: number;
  drift: number;
  latency?: { retrieve_p50_ms?: number; retrieve_p95_ms?: number };
};

export type UsedNodeSummary = { id: string; score?: number };

export type ChatUsedEvent = {
  graph_id: string;
  trace_id: string;
  turn_id: string;
  used_nodes: UsedNodeSummary[];
  ts: number;
};

export type ChatTokenEvent = {
  graph_id: string;
  trace_id: string;
  turn_id: string;
  role: string;
  token: string;
  index: number;
  done?: boolean;
  ts: number;
};

export type StreamHandlers = {
  onContract?: (c: StreamContract) => void;
  onFigDelta?: (d: FigDelta) => void;
  onChatStore?: (x: ChatStoreEvent) => void;
  onChatToken?: (x: ChatTokenEvent) => void;
  onToast?: (t: ToastEvent) => void;
  onMetrics?: (m: MetricsEvent) => void;
  onBenchPoint?: (p: BenchPoint) => void;
  onUsedNodes?: (nodes: UsedNodeSummary[]) => void;
  onPing?: (x: any) => void;
  onRaw?: (ev: { id?: string; event?: string; data?: string }) => void;
  onError?: (err: unknown) => void;
};

/* =============================== Helpers ================================== */

function parseJsonSafe<T>(s: string | undefined): T | null {
  if (!s) return null;
  try {
    return JSON.parse(s) as T;
  } catch {
    return null;
  }
}

function normBaseUrl(raw: unknown): string {
  const s = (typeof raw === "string" ? raw : "").trim();
  return s.replace(/\/+$/, "");
}

/**
 * Build stream URL.
 * - If graphId is provided → /stream?graph_id=...
 * - If graphId is omitted → /stream (backend resolves user's Universe)
 */
function buildStreamUrl(graphId?: string | null): string {
  const base = normBaseUrl(API_BASE_URL);
  // If API_BASE_URL is missing in the client bundle, keep UI alive with relative fallback
  const safeBase = base || "/api/v1";

  const gid = (graphId || "").trim();
  if (gid && gid.startsWith("U:")) {
    return `${safeBase}/stream?graph_id=${encodeURIComponent(gid)}`;
  }
  return `${safeBase}/stream`;
}

function parseSsePacket(packet: string): { id?: string; event?: string; data?: string } {
  let id: string | undefined;
  let event: string | undefined;
  const dataLines: string[] = [];

  // Normalize CRLF → LF to be safe
  const lines = packet.replace(/\r\n/g, "\n").split("\n");

  for (const line of lines) {
    if (!line) continue;
    if (line.startsWith(":")) continue; // comment
    if (line.startsWith("id:")) id = line.slice(3).trim();
    else if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }

  return { id, event, data: dataLines.join("\n") };
}

/* ========================== SSE (fetch reader) ============================ */

/**
 * startFaimStream
 * Production rule:
 *  - Pass graphId ONLY if you have a real Universe id (U:...).
 *  - Otherwise omit graphId and wait for "contract.universe.graph_id".
 */
export function startFaimStream(
  graphId: string | null | undefined,
  handlers: StreamHandlers
): () => void {
  const controller = new AbortController();

  let url: string;
  try {
    url = buildStreamUrl(graphId);
  } catch (err) {
    queueMicrotask(() => handlers.onError?.(err));
    return () => controller.abort();
  }

  let headers: HeadersInit;
  try {
    headers = buildFaimHeaders({
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    });
  } catch (err) {
    queueMicrotask(() => handlers.onError?.(err));
    return () => controller.abort();
  }

  const run = async () => {
    try {
      const res = await fetch(url, {
        method: "GET",
        headers,
        signal: controller.signal,
      });

      if (!res.ok) {
        let msg = `SSE connect failed: HTTP ${res.status}`;
        if (res.status === 401) msg = "SSE connect failed: missing API key";
        if (res.status === 403) msg = "SSE connect failed: invalid API key";
        throw new Error(msg);
      }
      if (!res.body) throw new Error("SSE connect failed: no response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buf = "";

      // Keep latest known universe id from the contract for fallback pings
      let universeGraphId: string | null = (graphId && graphId.trim()) ? graphId.trim() : null;

      const handleEvent = (ev: { id?: string; event?: string; data?: string }) => {
        handlers.onRaw?.(ev);

        switch (ev.event) {
          case "contract": {
            const x = parseJsonSafe<StreamContract>(ev.data);
            if (x) {
              universeGraphId = x.universe?.graph_id ?? universeGraphId;
              handlers.onContract?.(x);
            }
            break;
          }
          case "fig_delta": {
            const x = parseJsonSafe<FigDelta>(ev.data);
            if (x) handlers.onFigDelta?.(x);
            break;
          }
          case "chat_store": {
            const x = parseJsonSafe<ChatStoreEvent>(ev.data);
            if (x) handlers.onChatStore?.(x);
            break;
          }
          case "chat_token": {
            const x = parseJsonSafe<ChatTokenEvent>(ev.data);
            if (x) handlers.onChatToken?.(x);
            break;
          }
          case "toast": {
            const x = parseJsonSafe<ToastEvent>(ev.data);
            if (x) handlers.onToast?.(x);
            break;
          }
          case "metrics": {
            const x = parseJsonSafe<MetricsEvent>(ev.data);
            if (x) handlers.onMetrics?.(x);
            break;
          }
          case "bench_point": {
            const x = parseJsonSafe<BenchPoint>(ev.data);
            if (x) handlers.onBenchPoint?.(x);
            break;
          }
          case "used_nodes": {
            const x = parseJsonSafe<UsedNodeSummary[]>(ev.data);
            if (x) handlers.onUsedNodes?.(x);
            break;
          }
          case "chat_used": {
            const x = parseJsonSafe<ChatUsedEvent>(ev.data);
            if (x?.used_nodes) handlers.onUsedNodes?.(x.used_nodes);
            break;
          }
          case "ping": {
            const x = parseJsonSafe<any>(ev.data);
            // Ensure ping always has a graph_id for UI display even if backend omits it
            const fallback = {
              ts: Date.now(),
              graph_id: universeGraphId ?? undefined,
            };
            handlers.onPing?.(x ?? fallback);
            break;
          }
          default:
            break;
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });

        // SSE packets separated by blank line (either \n\n or \r\n\r\n)
        while (true) {
          // Normalize by searching for \n\n after CRLF normalization
          const normalized = buf.replace(/\r\n/g, "\n");
          const idx = normalized.indexOf("\n\n");
          if (idx < 0) break;

          const packet = normalized.slice(0, idx).trim();
          const rest = normalized.slice(idx + 2);

          // Rebuild original buf as normalized (we keep it normalized from now on)
          buf = rest;

          if (!packet) continue;
          handleEvent(parseSsePacket(packet));
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) handlers.onError?.(err);
    }
  };

  void run();
  return () => controller.abort();
}

/* ============================== React hook ================================ */

export function useFaimStream(
  graphId: string | null | undefined,
  handlers: StreamHandlers
) {
  const ref = useRef(handlers);
  ref.current = handlers;

  useEffect(() => {
    const stop = startFaimStream(graphId, {
      // Always use latest handlers via ref (prevents stale closures)
      onContract: (c) => ref.current.onContract?.(c),
      onFigDelta: (d) => ref.current.onFigDelta?.(d),
      onChatStore: (x) => ref.current.onChatStore?.(x),
      onChatToken: (x) => ref.current.onChatToken?.(x),
      onToast: (t) => ref.current.onToast?.(t),
      onMetrics: (m) => ref.current.onMetrics?.(m),
      onBenchPoint: (p) => ref.current.onBenchPoint?.(p),
      onUsedNodes: (n) => ref.current.onUsedNodes?.(n),
      onPing: (x) => ref.current.onPing?.(x),
      onRaw: (ev) => ref.current.onRaw?.(ev),
      onError: (e) => ref.current.onError?.(e),
    });

    return () => stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphId]);
}
