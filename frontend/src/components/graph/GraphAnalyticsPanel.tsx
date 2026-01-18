"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, PointerEvent, ReactNode } from "react";
import { API_BASE_URL, DEFAULT_GRAPH_ID, buildFaimHeaders } from "@/lib/api-client";

type DegreeBucket = {
  degree: number;
  count: number;
};

type ClusterStat = {
  cluster_id: number;
  count: number;
};

type GraphAnalyticsPanelProps = {
  graphId?: string;
};

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function readUniverseGraphId(): string {
  if (typeof window === "undefined") return "";
  return (window.localStorage.getItem("faim.universe_graph_id") || "").trim();
}

function getApiBase(): string {
  return (API_BASE_URL || "").trim().replace(/\/+$/, "");
}

/**
 * Sticky glow updater:
 * - updates --mx/--my on pointer move capture
 * - keeps last position (no reset on leave)
 * - controlled intensity (avoid "too much glow")
 */
function onStickyGlowMove(intensity = 0.2) {
  return (e: PointerEvent<HTMLElement>) => {
    const el = e.currentTarget as HTMLElement;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;
    el.style.setProperty("--mx", `${x.toFixed(2)}%`);
    el.style.setProperty("--my", `${y.toFixed(2)}%`);
    el.style.setProperty("--gvis", String(intensity));
  };
}

/** Small row glow used for cluster list items */
function GlowRow({ children }: { children: ReactNode }) {
  return (
    <div
      onPointerMoveCapture={onStickyGlowMove(0.16)}
      onPointerLeave={() => {}}
      style={
        {
          "--mx": "50%",
          "--my": "40%",
          "--gvis": "0",
        } as CSSProperties
      }
      className={[
        "group relative overflow-hidden rounded border border-slate-800 bg-slate-900/70 px-2 py-1",
        "transition duration-200 hover:border-cyan-500/30",
        "before:content-[''] before:pointer-events-none before:absolute before:inset-0",
        "before:[background:radial-gradient(420px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.10),transparent_66%)]",
        "before:opacity-[var(--gvis)]",
      ].join(" ")}
    >
      <div className="relative z-[1]">{children}</div>
    </div>
  );
}

const GraphAnalyticsPanel: React.FC<GraphAnalyticsPanelProps> = ({
  graphId,
}) => {
  const effectiveGraphId = useMemo(() => {
    const g = (graphId ?? "").trim();
    if (g.length > 0) return g;

    const u = readUniverseGraphId();
    if (u.length > 0) return u;

    return (DEFAULT_GRAPH_ID ?? "").trim();
  }, [graphId]);

  const [degreeBuckets, setDegreeBuckets] = useState<DegreeBucket[]>([]);
  const [clusters, setClusters] = useState<any[]>([]);
  const [redundancy, setRedundancy] = useState<any>(null);
  const [degError, setDegError] = useState<string | null>(null);
  const [cluError, setCluError] = useState<string | null>(null);
  const [redError, setRedError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Prevent duplicate calls in React StrictMode (dev) and on rapid re-renders
  const lastLoadKeyRef = useRef<string>("");
  const lastLoadAtRef = useRef<number>(0);

  useEffect(() => {
    let cancelled = false;

    const base = getApiBase();
    const loadKey = `${base || "(no-base)"}|${effectiveGraphId}`;

    // Dev-only: strict mode runs effects twice, avoid spamming endpoints
    const now = Date.now();
    if (
      lastLoadKeyRef.current === loadKey &&
      now - lastLoadAtRef.current < 800
    ) {
      return () => {
        cancelled = true;
      };
    }
    lastLoadKeyRef.current = loadKey;
    lastLoadAtRef.current = now;

    async function loadDegree(signal: AbortSignal) {
      setDegError(null);

      if (!base) {
        setDegreeBuckets([]);
        setDegError("Analytics disabled: API base is missing.");
        return;
      }

      if (!effectiveGraphId) {
        setDegreeBuckets([]);
        setDegError("Waiting for a valid graph id…");
        return;
      }

      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers = buildFaimHeaders();
      if (session && (session as any).accessToken) {
        (headers as any)["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const url = `${base}/graphs/${encodeURIComponent(effectiveGraphId)}/degree_distribution`;
      const res = await fetch(url, {
        cache: "no-store",
        headers,
        signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status}${text ? `: ${text}` : ""}`);
      }

      const body = await res.json();

      let buckets: DegreeBucket[] = [];

      if (Array.isArray(body)) {
        buckets = body
          .map((b: any) => ({
            degree: Number(b.degree ?? b.k ?? 0),
            count: Number(b.count ?? b.n ?? 0),
          }))
          .filter(
            (b: DegreeBucket) =>
              Number.isFinite(b.degree) && Number.isFinite(b.count),
          );
      } else if (Array.isArray((body as any)?.buckets)) {
        buckets = (body as any).buckets
          .map((b: any) => ({
            degree: Number(b.degree ?? b.k ?? 0),
            count: Number(b.count ?? b.n ?? 0),
          }))
          .filter(
            (b: DegreeBucket) =>
              Number.isFinite(b.degree) && Number.isFinite(b.count),
          );
      } else if (body && typeof body === "object") {
        buckets = Object.entries(body as Record<string, unknown>)
          .map(([k, v]) => ({
            degree: Number(k),
            count: Number(v),
          }))
          .filter(
            (b: DegreeBucket) =>
              Number.isFinite(b.degree) && Number.isFinite(b.count),
          );
      }

      buckets.sort((a, b) => a.degree - b.degree);

      if (!cancelled) setDegreeBuckets(buckets);
    }

    async function loadClusters(signal: AbortSignal) {
      setCluError(null);

      if (!base) {
        setClusters([]);
        setCluError("Analytics disabled: API base is missing.");
        return;
      }

      if (!effectiveGraphId) {
        setClusters([]);
        setCluError("Waiting for a valid graph id…");
        return;
      }

      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers = buildFaimHeaders();
      if (session && (session as any).accessToken) {
        (headers as any)["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      // Hit the NEW ops endpoint for rich data
      const url = `/api/ops/graphs/${encodeURIComponent(effectiveGraphId)}/clusters`;
      const res = await fetch(url, {
        cache: "no-store",
        headers,
        signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        setCluError(`Failed to load semantic clusters: ${res.status}`);
        return;
      }

      const body = await res.json();
      if (!cancelled) setClusters(body || []);
    }

    async function loadRedundancy(signal: AbortSignal) {
      setRedError(null);
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers = buildFaimHeaders();
      if (session && (session as any).accessToken) {
        (headers as any)["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const url = `/api/ops/graphs/${encodeURIComponent(effectiveGraphId)}/redundancy`;
      try {
        const res = await fetch(url, {
          headers,
          signal
        });
        if (res.ok) {
          const body = await res.json();
          if (!cancelled) setRedundancy(body);
        }
      } catch (err) {
        console.error("Redundancy load fail:", err);
      }
    }

    async function loadAll() {
      const controller = new AbortController();

      try {
        setLoading(true);
        await Promise.allSettled([
          loadDegree(controller.signal),
          loadClusters(controller.signal),
          loadRedundancy(controller.signal),
        ]);
      } catch (err) {
        // individual loaders set errors; this is just a safety net
      } finally {
        if (!cancelled) setLoading(false);
      }

      return () => controller.abort();
    }

    let cleanupAbort: (() => void) | undefined;

    loadAll().then((fn) => {
      cleanupAbort = fn;
    });

    return () => {
      cancelled = true;
      if (cleanupAbort) cleanupAbort();
    };
  }, [effectiveGraphId]);

  const maxCount = useMemo(
    () => degreeBuckets.reduce((m, b) => (b.count > m ? b.count : m), 0),
    [degreeBuckets],
  );

  return (
    <section
      onPointerMoveCapture={onStickyGlowMove(0.2)}
      onPointerLeave={() => {}}
      style={
        {
          "--mx": "52%",
          "--my": "28%",
          "--gvis": "0",
        } as CSSProperties
      }
      className={[
        "group relative overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4 text-xs",
        "ring-1 ring-inset ring-cyan-500/10",
        "transition duration-200 hover:border-cyan-500/35",
        "shadow-[0_0_0_1px_rgba(15,23,42,0.55),0_18px_70px_-40px_rgba(0,0,0,0.85)]",
        "before:content-[''] before:pointer-events-none before:absolute before:inset-0",
        "after:content-[''] after:pointer-events-none after:absolute after:inset-0",
        "before:[background:radial-gradient(620px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.11),transparent_66%)]",
        "before:opacity-[var(--gvis)]",
        "after:[background:radial-gradient(460px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.09),transparent_70%)]",
        "after:opacity-[var(--gvis)]",
      ].join(" ")}
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />

      <div className="relative z-[1]">
        <header className="mb-2 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-semibold text-slate-100">
              Graph analytics
            </h2>
            <p className="text-[11px] text-slate-400">
              Degree distribution and prototype cluster map.
            </p>
          </div>
          {loading && (
            <span className="text-[10px] text-slate-500">Loading…</span>
          )}
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          {/* Degree distribution & Redundancy */}
          <div className="space-y-4">
            <div>
              <h3 className="mb-1 text-[11px] font-semibold text-slate-200">
                Degree distribution
              </h3>

              {degError ? (
                <p className="rounded border border-red-900/50 bg-red-950/40 px-2 py-1 text-[11px] text-red-100">
                  {degError}
                </p>
              ) : degreeBuckets.length === 0 ? (
                <p className="rounded border border-dashed border-slate-700 bg-slate-950/60 px-2 py-3 text-[11px] text-slate-500">
                  No degree data available.
                </p>
              ) : (
                <div className="h-24 rounded bg-slate-950/80 p-2">
                  <svg viewBox="0 0 220 80" className="h-full w-full">
                    {degreeBuckets.map((b, i) => {
                      const barWidth = 220 / Math.max(degreeBuckets.length, 1);
                      const x = i * barWidth + 2;
                      const ratio = maxCount > 0 ? b.count / maxCount : 0;
                      const height = ratio * 70;
                      const y = 78 - height;
                      return (
                        <rect
                          key={b.degree}
                          x={x}
                          y={y}
                          width={barWidth - 4}
                          height={height}
                          rx={1.5}
                          className="fill-cyan-500/50"
                        />
                      );
                    })}
                  </svg>
                </div>
              )}
            </div>

            {/* Redundancy Metric */}
            {redundancy && (
              <div className="p-3 bg-slate-900/40 border border-slate-800 rounded-xl">
                 <div className="flex justify-between items-center mb-1.5">
                   <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Redundancy Index</h4>
                   <span className="text-[10px] font-mono text-cyan-400">{(redundancy.mean_cosine * 100).toFixed(1)}%</span>
                 </div>
                 <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-cyan-500 transition-all duration-1000" 
                      style={{ width: `${redundancy.mean_cosine * 100}%` }}
                    />
                 </div>
                 <p className="mt-2 text-[9px] text-slate-500 leading-tight">
                    Measures system noise. Lower values indicate better antisymmetric cancellation.
                 </p>
              </div>
            )}
          </div>

          {/* Cluster map */}
          <div className="flex flex-col h-full">
            <h3 className="mb-2 text-[11px] font-semibold text-slate-200">
              Semantic Clusters
            </h3>

            {cluError ? (
              <p className="rounded border border-red-900/50 bg-red-950/40 px-2 py-1 text-[11px] text-red-100">
                {cluError}
              </p>
            ) : clusters.length === 0 ? (
              <p className="rounded border border-dashed border-slate-700 bg-slate-950/60 px-2 py-3 text-[11px] text-slate-500">
                Awaiting clustering signal...
              </p>
            ) : (
              <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
                {clusters.map((c) => (
                  <div key={c.cluster_id} className="group p-2 bg-slate-900/50 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full" style={{ backgroundColor: c.color }} />
                        <span className="text-[11px] font-bold text-slate-200 group-hover:text-cyan-400 transition-colors">
                          {c.label}
                        </span>
                      </div>
                      <span className="text-[9px] font-mono text-slate-500">
                        {c.node_ids.length} NODES
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 line-clamp-1 group-hover:line-clamp-none transition-all">
                      {c.description}
                    </p>
                    <div className="mt-1.5 flex items-center justify-between text-[8px] font-mono text-slate-600">
                      <span>ID: {c.cluster_id}</span>
                      <span>COHERENCE: {(c.coherence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default GraphAnalyticsPanel;
