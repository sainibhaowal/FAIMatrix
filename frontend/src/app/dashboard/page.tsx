// /home/ravi_saini/FAIM/frontend/src/app/dashboard/page.tsx
"use client";

/* ========================================================================== */
/*  FAIM LAB — Dashboard Page (Golden Edition / Production Wiring Fix)         */
/* -------------------------------------------------------------------------- */
/*  FIXES (UI-ONLY, NO BACKEND CHANGES):                                       */
/*   - Define entryGraphId (was undefined -> crash)                            */
/*   - Start SSE immediately using entryGraphId (e.g. "MAIN")                  */
/*   - On SSE contract: switch to REAL per-user universe graph_id ("U:...")    */
/*   - Never ask user for graph_id; universe is resolved server-side           */
/*   - Persist universe id locally for stable refresh                          */
/*   - Debounced metrics refresh to avoid endpoint spam                        */
/* ========================================================================== */

import type React from "react";
import { useEffect, useRef, useState, type CSSProperties } from "react";

import {
  useFaimStream,
  type FigDelta,
  type StreamContract,
  type BenchPoint as SseBenchPoint,
  type MetricsEvent as SseMetricsEvent,
  type ChatStoreEvent,
  type UsedNodeSummary as SseUsedNode,
} from "@/lib/realtime";

import {
  API_BASE_URL,
  DEFAULT_GRAPH_ID,
  fetchHealth,
  fetchBenchmarks,
  type HealthStatus,
  type BenchmarkPoint,
  type UsedNodeSummary as ApiUsedNode,
  buildFaimHeaders,
} from "@/lib/api";

import {
  MemoryTimeline,
  type MemoryEvent,
  type SpeedTier,
} from "@/components/MemoryTimeline";

import SystemRuntimePanel from "@/components/SystemRuntimePanel";

/* ========================================================================== */
/*  Types (Dashboard-local normalized view)                                    */
/* ========================================================================== */

type DashboardMetrics = {
  nodes: number;
  cr: number;
  redundancy: number;
  drift: number;
  raw_bytes?: number;
  faim_bytes?: number;
  latency?: {
    retrieve_p50_ms?: number;
    retrieve_p95_ms?: number;
  };
};

type EvolutionStatus = {
  graph_id?: string;
  status?: "ok" | "error" | "idle";
  last_run_ts?: number | null;
  last_duration_ms?: number | null;
  last_error?: string | null;
  runs?: number;
  last_stats?: {
    merges?: number;
    prunes?: number;
    promotions?: number;
  } | null;
};

type Accent = "cyan" | "violet" | "ok" | "warn" | "error" | "neutral";

/* ========================================================================== */
/*  Small local storage helpers (NO api.ts edits)                              */
/* ========================================================================== */

const LS_UNIVERSE_GRAPH_ID = "faim_universe_graph_id";

function safeSetLocalStorage(key: string, value: string) {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

function safeGetLocalStorage(key: string): string | null {
  try {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

/* ========================================================================== */
/*  Helpers                                                                    */
/* ========================================================================== */

function inferSpeedTier(nodes: number): SpeedTier {
  if (nodes < 50_000) return "HOT";
  if (nodes < 250_000) return "WARM";
  return "COLD";
}

function parseJsonSafe<T>(x: unknown): T | null {
  if (!x) return null;
  if (typeof x === "object") return x as T;
  if (typeof x === "string") {
    try {
      return JSON.parse(x) as T;
    } catch {
      return null;
    }
  }
  return null;
}

function formatBytes(bytes?: number | null): string {
  const n = typeof bytes === "number" && Number.isFinite(bytes) ? bytes : 0;
  if (n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let idx = 0;
  let value = n;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${units[idx]}`;
}

/**
 * Coerce metrics from either:
 *  A) backend /graphs/{id}/metrics (flat keys)
 *  B) SSE "metrics" event (already in nodes/cr shape)
 */
function coerceDashboardMetrics(input: unknown): DashboardMetrics | null {
  const parsed = parseJsonSafe<any>(input);
  const x = parsed?.cards && typeof parsed.cards === "object" ? parsed.cards : parsed;
  if (!x) return null;

  // Backend-flat shape
  const node_count = typeof x.node_count === "number" ? x.node_count : undefined;
  const compression_ratio =
    typeof x.compression_ratio === "number" ? x.compression_ratio : undefined;

  // SSE shape
  const nodes = typeof x.nodes === "number" ? x.nodes : undefined;
  const cr = typeof x.cr === "number" ? x.cr : undefined;

  const outNodes =
    typeof node_count === "number"
      ? node_count
      : typeof nodes === "number"
        ? nodes
        : 0;

  const outCr =
    typeof compression_ratio === "number"
      ? compression_ratio
      : typeof cr === "number"
        ? cr
        : 1;

  const redundancy = typeof x.redundancy === "number" ? x.redundancy : 0;
  const drift = typeof x.drift === "number" ? x.drift : 0;

  const raw_bytes =
    typeof x.raw_bytes === "number"
      ? x.raw_bytes
      : typeof x.raw === "number"
        ? x.raw
        : undefined;
  const faim_bytes =
    typeof x.faim_bytes === "number"
      ? x.faim_bytes
      : typeof x.vector_bytes === "number"
        ? x.vector_bytes
        : typeof x.processed_bytes === "number"
          ? x.processed_bytes
          : undefined;

  const retrieve_p50_ms =
    typeof x.retrieve_p50_ms === "number"
      ? x.retrieve_p50_ms
      : typeof x?.latency?.retrieve_p50_ms === "number"
        ? x.latency.retrieve_p50_ms
        : undefined;

  const retrieve_p95_ms =
    typeof x.retrieve_p95_ms === "number"
      ? x.retrieve_p95_ms
      : typeof x?.latency?.retrieve_p95_ms === "number"
        ? x.latency.retrieve_p95_ms
        : undefined;

  return {
    nodes: outNodes,
    cr: outCr,
    redundancy,
    drift,
    raw_bytes,
    faim_bytes,
    latency:
      retrieve_p50_ms !== undefined || retrieve_p95_ms !== undefined
        ? { retrieve_p50_ms, retrieve_p95_ms }
        : undefined,
  };
}

async function loadGraphMetrics(graphId: string): Promise<DashboardMetrics | null> {
  if (!graphId) return null;
  try {
    const res = await fetch(
      `${API_BASE_URL}/graphs/${encodeURIComponent(graphId)}/metrics`,
      { cache: "no-store", headers: buildFaimHeaders() },
    );
    if (!res.ok) return null;
    const raw = await res.json();
    return coerceDashboardMetrics(raw);
  } catch {
    return null;
  }
}

async function loadRecentUsedNodes(
  graphId: string,
  limit: number = 20,
): Promise<ApiUsedNode[]> {
  if (!graphId) return [];
  try {
    const res = await fetch(
      `${API_BASE_URL}/graphs/${encodeURIComponent(graphId)}/recent-used-nodes?limit=${limit}`,
      { cache: "no-store", headers: buildFaimHeaders() },
    );
    if (!res.ok) return [];
    const data = (await res.json()) as ApiUsedNode[];
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

async function loadEvolutionStatus(graphId: string): Promise<EvolutionStatus | null> {
  if (!graphId) return null;
  try {
    const res = await fetch(
      `${API_BASE_URL}/evolution/status?graph_id=${encodeURIComponent(graphId)}`,
      { cache: "no-store", headers: buildFaimHeaders() },
    );
    if (!res.ok) return null;
    const raw = await res.json();
    return raw as EvolutionStatus;
  } catch {
    return null;
  }
}

function coerceBenchPoint(input: unknown): BenchmarkPoint | null {
  const x = parseJsonSafe<any>(input);
  if (!x) return null;

  const timestamp =
    typeof x.timestamp === "string"
      ? x.timestamp
      : typeof x.ts === "number"
        ? new Date(x.ts * 1000).toISOString()
        : new Date().toISOString();

  const nodes =
    typeof x.nodes === "number"
      ? x.nodes
      : typeof x.node_count === "number"
        ? x.node_count
        : 0;

  const cr =
    typeof x.cr === "number"
      ? x.cr
      : typeof x.compression_ratio === "number"
        ? x.compression_ratio
        : 1;

  const redundancy = typeof x.redundancy === "number" ? x.redundancy : 0;
  const drift = typeof x.drift === "number" ? x.drift : 0;

  const p50 =
    typeof x?.latency?.retrieve_p50_ms === "number"
      ? x.latency.retrieve_p50_ms
      : typeof x.retrieve_p50_ms === "number"
        ? x.retrieve_p50_ms
        : 0;

  const p95 =
    typeof x?.latency?.retrieve_p95_ms === "number"
      ? x.latency.retrieve_p95_ms
      : typeof x.retrieve_p95_ms === "number"
        ? x.retrieve_p95_ms
        : 0;

  return {
    timestamp,
    nodes,
    cr,
    redundancy,
    drift,
    latency: { retrieve_p50_ms: p50, retrieve_p95_ms: p95 },
  };
}

/* ========================================================================== */
/*  Page                                                                       */
/* ========================================================================== */

import { useUserIds } from "@/contexts/UserContext";

// ...

export default function DashboardPage() {
  // "MAIN" (or env override) is ONLY an entry alias. Real universe is resolved by backend via SSE contract.
  const entryGraphId = DEFAULT_GRAPH_ID;

  // Boot strategy:
  // 1) Use last-known universe (if any) for fast refresh
  // 2) Otherwise use entryGraphId to connect SSE and let contract resolve universe
  const [streamGraphId, setStreamGraphId] = useState<string>(entryGraphId);
  const [metricsGraphId, setMetricsGraphId] = useState<string>(entryGraphId);

  const [sseStatus, setSseStatus] = useState<"connecting" | "live" | "error">(
    "connecting",
  );

  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [mounted, setMounted] = useState(false);

  // AUTH SYNC: Get authoritative IDs from UserContext (handles stale localStorage)
  const { graphId: contextGraphId } = useUserIds();

  // Effect: Sync local state with Context whenever it updates
  useEffect(() => {
    if (contextGraphId && contextGraphId.startsWith("U:")) {
       // Context is authoritative (fetched from DB)
       setStreamGraphId(contextGraphId);
       setMetricsGraphId(contextGraphId);
    } else {
       // Fallback: try storage if context not ready
       const u =
        safeGetLocalStorage("faim.universe_graph_id") ||
        safeGetLocalStorage(LS_UNIVERSE_GRAPH_ID);
       if (u && u.startsWith("U:")) {
         setStreamGraphId(u);
         setMetricsGraphId(u);
       }
    }
  }, [contextGraphId]);

  useEffect(() => {
    setMounted(true);
  }, []);

  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [recentNodes, setRecentNodes] = useState<ApiUsedNode[]>([]);
  const [events, setEvents] = useState<MemoryEvent[]>([]);
  const [benchPoints, setBenchPoints] = useState<BenchmarkPoint[]>([]);
  const [evolution, setEvolution] = useState<EvolutionStatus | null>(null);

  // Debounced refresh (avoid spamming metrics endpoint)
  const refreshTimerRef = useRef<number | null>(null);

  // Avoid stale closure for graph id inside setTimeout
  const metricsGraphIdRef = useRef(metricsGraphId);
  useEffect(() => {
    metricsGraphIdRef.current = metricsGraphId;
  }, [metricsGraphId]);

  function scheduleRefreshMetrics(delayMs = 200) {
    if (refreshTimerRef.current) window.clearTimeout(refreshTimerRef.current);
    refreshTimerRef.current = window.setTimeout(async () => {
      const gid = metricsGraphIdRef.current;
      const m = await loadGraphMetrics(gid);
      if (m) setMetrics(m);
    }, delayMs);
  }

  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) window.clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    };
  }, []);

  // Initial REST load (and reload when metricsGraphId changes)
  useEffect(() => {
    let alive = true;
    const gid = metricsGraphId;

    (async () => {
      try {
        const [h, b, m, rn, ev] = await Promise.all([
          fetchHealth(),
          fetchBenchmarks(gid).catch(() => [] as BenchmarkPoint[]),
          loadGraphMetrics(gid),
          loadRecentUsedNodes(gid, 20),
          loadEvolutionStatus(gid),
        ]);

        if (!alive) return;

        setHealth(h);
        setHealthError(null);

        setBenchPoints(Array.isArray(b) ? b : []);
        setRecentNodes(Array.isArray(rn) ? rn : []);
        setEvolution(ev);
        if (m) setMetrics(m);
      } catch (e) {
        if (!alive) return;
        console.warn("[dashboard] initial load failed:", e);
        setHealth(null);
        setHealthError("Unable to reach FAIM backend.");
      }
    })();

    return () => {
      alive = false;
    };
  }, [metricsGraphId]);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const gid = metricsGraphId;
      const ev = await loadEvolutionStatus(gid);
      if (!cancelled && ev) setEvolution(ev);
    };
    void tick();
    const id = window.setInterval(() => void tick(), 15000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [metricsGraphId]);

  // SSE wiring: contract/fig_delta/chat_* -> trigger refresh
  useFaimStream(streamGraphId, {
    onContract: (c: StreamContract) => {
      setSseStatus("live");

      const ug = c?.universe?.graph_id;
      if (ug && ug.startsWith("U:")) {
        // Lock everything to the REAL per-user universe ID
        safeSetLocalStorage("faim.universe_graph_id", ug);
        safeSetLocalStorage(LS_UNIVERSE_GRAPH_ID, ug);
        setStreamGraphId(ug);
        setMetricsGraphId(ug);
      }

      scheduleRefreshMetrics(50);
    },

    onFigDelta: (d: FigDelta) => {
      setSseStatus("live");
      scheduleRefreshMetrics(150);

      const added = d.delta?.nodes_added?.length ?? 0;
      const removed = d.delta?.nodes_removed?.length ?? 0;

      const ev: MemoryEvent = {
        id: `delta-${Date.now()}`,
        timestamp: new Date().toISOString(),
        kind: "delta",
        label: "Graph delta",
        details: `+${added} nodes, -${removed} nodes.`,
        speedTier: inferSpeedTier(metrics?.nodes ?? 0),
      };

      setEvents((prev) => [ev, ...prev].slice(0, 200));
    },

    onChatStore: (x: ChatStoreEvent) => {
      setSseStatus("live");
      scheduleRefreshMetrics(120);

      const ev: MemoryEvent = {
        id: `chat_store-${Date.now()}`,
        timestamp: new Date().toISOString(),
        kind: "delta",
        label: "Chat stored to memory",
        details: x.summary || `stored nodes=${x.created_node_ids?.length ?? 0}`,
        speedTier: inferSpeedTier(metrics?.nodes ?? 0),
      };
      setEvents((prev) => [ev, ...prev].slice(0, 200));
    },

    onUsedNodes: (nodes: SseUsedNode[] | any) => {
      setSseStatus("live");

      // Map SSE used nodes -> recent list (soft fallback)
      if (Array.isArray(nodes)) {
        const mapped: ApiUsedNode[] = nodes.slice(0, 20).map((n) => ({
          node_id: String((n as any).id ?? ""),
          score: typeof (n as any).score === "number" ? (n as any).score : 0,
          snippet: undefined,
        }));
        setRecentNodes(mapped);
      }

      scheduleRefreshMetrics(120);
    },

    onBenchPoint: (p: SseBenchPoint) => {
      setSseStatus("live");

      const bp = coerceBenchPoint(p);
      if (bp) setBenchPoints((prev) => [...prev.slice(-199), bp]);

      scheduleRefreshMetrics(150);
    },

    onMetrics: (m: SseMetricsEvent) => {
      setSseStatus("live");
      const coerced = coerceDashboardMetrics(m);
      if (coerced) setMetrics(coerced);
    },

    onError: (e) => {
      setSseStatus("error");
      console.error("[dashboard] SSE error:", e);
    },
  });

  const m = metrics;

  const nodeCount = m?.nodes ?? 0;
  const cr = m?.cr ?? 1;
  const redundancy = m?.redundancy ?? 0;
  const drift = m?.drift ?? 0;
  const rawBytes = m?.raw_bytes;
  const faimBytes = m?.faim_bytes;
  const storageValue = m
    ? `${formatBytes(rawBytes)} → ${formatBytes(faimBytes)}`
    : "—";

  const p50 = m?.latency?.retrieve_p50_ms;
  const p95 = m?.latency?.retrieve_p95_ms;

  const evolutionStatus = evolution?.status ?? "idle";
  const evolutionRuns = evolution?.runs ?? 0;
  const evolutionLastRun = evolution?.last_run_ts
    ? new Date(evolution.last_run_ts * 1000)
    : null;
  const evolutionHint = evolutionLastRun
    ? `Last run ${evolutionLastRun.toLocaleTimeString()} · runs ${evolutionRuns}`
    : "No evolution runs yet.";

  return (
    <div className="space-y-6">
      {/* Top row: FAIM health + core numbers */}
      <section>
        <header className="mb-3">
          <h1 className="text-sm font-semibold text-slate-100">FAIM Health</h1>
          <p className="text-xs text-slate-400">
            High-level status of the memory engine in one glance.
          </p>
        </header>

        <div className="grid gap-3 text-xs md:grid-cols-3 xl:grid-cols-6">
          <StatCard
            label="Status"
            value={
              health?.status
                ? health.status.toUpperCase()
                : healthError
                  ? "UNKNOWN"
                  : "…"
            }
            hint={healthError ? healthError : "Reported by /api/v1/health."}
            accent={
              health?.status === "ok"
                ? "ok"
                : health?.status === "degraded"
                  ? "warn"
                  : health?.status === "down"
                    ? "error"
                    : "neutral"
            }
          />

          <StatCard
            label="Backend version"
            value={health?.version ?? "—"}
            hint="Backend build/version string."
          />

          <StatCard
            label="Nodes"
            value={nodeCount.toLocaleString()}
            hint="Total logical nodes in your Universe (metrics)."
          />

          <StatCard
            label="Storage"
            value={storageValue}
            hint="Raw payload bytes → FAIM vector bytes (estimate)."
            accent="cyan"
          />

          <StatCard
            label="Evolution"
            value={evolutionStatus.toUpperCase()}
            hint={evolutionHint}
            accent={evolutionStatus === "error" ? "error" : "ok"}
          />

          <StatCard
            label="SSE"
            value={sseStatus.toUpperCase()}
            hint={
              mounted
                ?`stream=${streamGraphId} | metrics=${metricsGraphId} | entry=${entryGraphId}`
                : "connecting..."              
              }
            accent={sseStatus === "live" ? "ok" : sseStatus === "error" ? "error" : "neutral"}
          />
        </div>
      </section>

      {/* Middle row: graph summary metrics */}
      <section>
        <header className="mb-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Graph summary
          </h2>
        </header>

        <div className="grid gap-3 text-xs md:grid-cols-3 xl:grid-cols-6">
          <StatCard
            label="Compression ratio (CR)"
            value={cr.toFixed(3)}
            hint="Higher = stronger compression of raw bytes."
            accent="cyan"
          />
          <StatCard
            label="Redundancy (R)"
            value={redundancy.toFixed(3)}
            hint="How much duplicated information remains."
            accent="violet"
          />
          <StatCard
            label="Drift"
            value={drift.toFixed(3)}
            hint="How much the memory distribution drifts over time."
            accent="cyan"
          />
          <StatCard
            label="Retrieve p50 (ms)"
            value={p50 !== undefined ? p50.toFixed(1) : "—"}
            hint="Median retrieval latency."
            accent="violet"
          />
          <StatCard
            label="Retrieve p95 (ms)"
            value={p95 !== undefined ? p95.toFixed(1) : "—"}
            hint="Tail retrieval latency (95th percentile)."
            accent="violet"
          />
          <StatCard
            label="Universe (graph_id)"
            value={mounted ? (metricsGraphId || "—") : "—"}
            hint="Your permanent Universe ID (assigned at account creation)."
          />
        </div>

        <div className="mt-3 space-y-3">
          <SpeedTierBanner metrics={m} />
          <BenchmarkSparkline points={benchPoints} />
        </div>
      </section>

      {/* Optional system panel (kept as-is) */}
      <SystemRuntimePanel />

      {/* Bottom: recent activity + memory timeline */}
      <section className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-4 text-xs lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1.2fr)]">
        <div>
          <header className="mb-2 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-xs font-semibold text-slate-100">
                Recent activity
              </h2>
              <p className="text-[11px] text-slate-400">
                Last used nodes (endpoint or SSE fallback).
              </p>
            </div>
          </header>

          {recentNodes.length === 0 ? (
            <p className="text-[11px] text-slate-500">
              No recent nodes available yet. This will populate after chat activity
              (SSE chat_used) or when backend recent-used endpoint is enabled.
            </p>
          ) : (
            <ul className="divide-y divide-slate-800">
              {recentNodes.map((n, idx) => {
                const scoreLabel = n.score !== undefined ? n.score.toFixed(2) : "—";
                const key = `${n.node_id || "node"}-${idx}`;

                return (
                  <li key={key} className="py-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="truncate text-[11px] font-medium text-slate-100">
                        {n.snippet || "(no snippet)"}
                      </div>
                      <div className="shrink-0 rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                        score {scoreLabel}
                      </div>
                    </div>
                    <div className="mt-1 truncate text-[10px] text-slate-500">
                      {n.node_id}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="border-l border-slate-800 pl-4 lg:pl-6">
          <MemoryTimeline events={events} />
        </div>
      </section>
    </div>
  );
}

/* ========================================================================== */
/*  StatCard                                                                   */
/* ========================================================================== */

function StatCard({
  label,
  value,
  hint,
  accent = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  accent?: Accent;
}) {
  let border = "border-slate-800/80";
  let chip = "bg-slate-800 text-slate-200";
  let glowA = "rgba(34,211,238,0.14)";
  let glowB = "rgba(139,92,246,0.10)";

  if (accent === "cyan") {
    border = "border-cyan-500/20";
    chip = "bg-cyan-500/10 text-cyan-100 ring-1 ring-inset ring-cyan-400/20";
    glowA = "rgba(34,211,238,0.16)";
    glowB = "rgba(139,92,246,0.10)";
  } else if (accent === "violet") {
    border = "border-violet-500/20";
    chip =
      "bg-violet-500/10 text-violet-100 ring-1 ring-inset ring-violet-400/20";
    glowA = "rgba(139,92,246,0.16)";
    glowB = "rgba(34,211,238,0.10)";
  } else if (accent === "ok") {
    border = "border-emerald-500/25";
    chip =
      "bg-emerald-500/10 text-emerald-100 ring-1 ring-inset ring-emerald-400/25";
    glowA = "rgba(16,185,129,0.14)";
    glowB = "rgba(34,211,238,0.08)";
  } else if (accent === "warn") {
    border = "border-amber-500/25";
    chip =
      "bg-amber-500/10 text-amber-100 ring-1 ring-inset ring-amber-400/25";
    glowA = "rgba(245,158,11,0.14)";
    glowB = "rgba(139,92,246,0.08)";
  } else if (accent === "error") {
    border = "border-rose-500/25";
    chip =
      "bg-rose-500/10 text-rose-100 ring-1 ring-inset ring-rose-400/25";
    glowA = "rgba(244,63,94,0.14)";
    glowB = "rgba(34,211,238,0.08)";
  }

  const onEnter = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    if (!el.style.getPropertyValue("--sx") || !el.style.getPropertyValue("--sy")) {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--sx", `${Math.round(r.width / 2)}px`);
      el.style.setProperty("--sy", `${Math.round(r.height / 2)}px`);
    }
  };

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    const x = Math.round(e.clientX - r.left);
    const y = Math.round(e.clientY - r.top);
    el.style.setProperty("--sx", `${x}px`);
    el.style.setProperty("--sy", `${y}px`);
  };

  return (
    <div
      onMouseEnter={onEnter}
      onMouseMove={onMove}
      className={[
        "group relative overflow-hidden rounded-2xl border",
        border,
        "bg-slate-950/35 backdrop-blur-xl",
        "shadow-[0_10px_30px_-18px_rgba(0,0,0,0.9)]",
        "transition-transform duration-200 ease-out will-change-transform",
        "hover:-translate-y-[2px]",
        "hover:shadow-[0_18px_50px_-26px_rgba(34,211,238,0.28)]",
        "p-4",
      ].join(" ")}
      style={{} as CSSProperties}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
        style={{
          background: `radial-gradient(520px circle at var(--sx) var(--sy), ${glowA}, transparent 55%)`,
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
        style={{
          background: `radial-gradient(900px circle at var(--sx) var(--sy), ${glowB}, transparent 60%)`,
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px opacity-60"
        style={{
          background:
            "linear-gradient(90deg, transparent, rgba(255,255,255,0.10), transparent)",
        }}
      />

      <div className="relative">
        <div className="flex items-center justify-between gap-3">
          <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            {label}
          </div>

          <span
            className={[
              "rounded-full px-2.5 py-1 text-[10px]",
              chip,
              "transition-transform duration-200 ease-out",
              "group-hover:scale-[1.02]",
            ].join(" ")}
          >
            {value}
          </span>
        </div>

        {hint && (
          <p className="mt-2 text-[11px] leading-snug text-slate-500">{hint}</p>
        )}
      </div>
    </div>
  );
}

/* ========================================================================== */
/*  Speed Tier Banner                                                          */
/* ========================================================================== */

function SpeedTierBanner({ metrics }: { metrics: DashboardMetrics | null }) {
  if (!metrics) {
    return (
      <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-3 text-[11px] text-slate-500">
        Waiting for first metrics from backend…
      </div>
    );
  }

  const tier = inferSpeedTier(metrics.nodes ?? 0);
  const label =
    tier === "HOT"
      ? "HOT tier: everything in fast memory. Great for interactive debugging and demos."
      : tier === "WARM"
        ? "WARM tier: mixed hot + compressed segments. Balanced speed vs. capacity."
        : "COLD tier: majority compressed/cold. Focus on recall & CR, expect higher latency.";

  return (
    <div className="rounded-lg border border-cyan-500/40 bg-cyan-500/10 p-3 text-[11px] text-cyan-100">
      <div className="text-xs font-semibold">Speed tier: {tier}</div>
      <p className="mt-1 text-[11px] text-cyan-100/90">{label}</p>
    </div>
  );
}

/* ========================================================================== */
/*  Benchmark Sparkline                                                        */
/* ========================================================================== */

function BenchmarkSparkline({ points }: { points: BenchmarkPoint[] }) {
  if (!points || points.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-3 text-[11px] text-slate-500">
        No benchmark data yet. Run benchmark scripts to see a CR trend here.
      </div>
    );
  }

  const maxPoints = 40;
  const series = points.slice(-maxPoints);
  const values = series.map((p) => (typeof p.cr === "number" ? p.cr : 1));

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  const width = 100;
  const height = 32;
  const xStep = values.length > 1 ? width / (values.length - 1) : width;

  const pointsAttr = values
    .map((v, i) => {
      const x = i * xStep;
      const norm = (v - min) / span;
      const y = height - 4 - norm * 24;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  const latest = values[values.length - 1];

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-[11px]">
      <div className="mb-1 flex items-center justify-between gap-2">
        <div className="text-[11px] uppercase tracking-wide text-slate-400">
          Benchmark CR trend
        </div>
        <div className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-200">
          latest CR {latest.toFixed(3)}
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-16 w-full"
        preserveAspectRatio="none"
      >
        <polyline
          fill="none"
          stroke="rgb(56 189 248)"
          strokeWidth="1.5"
          points={pointsAttr}
        />
      </svg>

      <p className="mt-1 text-[10px] text-slate-500">
        Compression ratio across recent benchmark runs.
      </p>
    </div>
  );
}
