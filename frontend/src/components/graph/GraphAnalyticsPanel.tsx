'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, PointerEvent, ReactNode } from 'react';
import { API_BASE_URL, DEFAULT_GRAPH_ID, buildFaimHeaders } from '@/lib/api';

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
  if (typeof window === 'undefined') return '';
  return (window.localStorage.getItem('faim.universe_graph_id') || '').trim();
}

function getApiBase(): string {
  return (API_BASE_URL || '').trim().replace(/\/+$/, '');
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
    el.style.setProperty('--mx', `${x.toFixed(2)}%`);
    el.style.setProperty('--my', `${y.toFixed(2)}%`);
    el.style.setProperty('--gvis', String(intensity));
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
          '--mx': '50%',
          '--my': '40%',
          '--gvis': '0',
        } as CSSProperties
      }
      className={[
        'group relative overflow-hidden rounded border border-slate-800 bg-slate-900/70 px-2 py-1',
        'transition duration-200 hover:border-cyan-500/30',
        "before:content-[''] before:pointer-events-none before:absolute before:inset-0",
        'before:[background:radial-gradient(420px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.10),transparent_66%)]',
        'before:opacity-[var(--gvis)]',
      ].join(' ')}
    >
      <div className="relative z-[1]">{children}</div>
    </div>
  );
}

const GraphAnalyticsPanel: React.FC<GraphAnalyticsPanelProps> = ({ graphId }) => {
  const effectiveGraphId = useMemo(() => {
    const g = (graphId ?? '').trim();
    if (g.length > 0) return g;

    const u = readUniverseGraphId();
    if (u.length > 0) return u;

    return (DEFAULT_GRAPH_ID ?? '').trim();
  }, [graphId]);

  const [degreeBuckets, setDegreeBuckets] = useState<DegreeBucket[]>([]);
  const [clusters, setClusters] = useState<ClusterStat[]>([]);
  const [degError, setDegError] = useState<string | null>(null);
  const [cluError, setCluError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Prevent duplicate calls in React StrictMode (dev) and on rapid re-renders
  const lastLoadKeyRef = useRef<string>('');
  const lastLoadAtRef = useRef<number>(0);

  useEffect(() => {
    let cancelled = false;

    const base = getApiBase();
    const loadKey = `${base || '(no-base)'}|${effectiveGraphId}`;

    // Dev-only: strict mode runs effects twice, avoid spamming endpoints
    const now = Date.now();
    if (lastLoadKeyRef.current === loadKey && now - lastLoadAtRef.current < 800) {
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
        setDegError('Analytics disabled: API base is missing.');
        return;
      }

      if (!effectiveGraphId) {
        setDegreeBuckets([]);
        setDegError('Waiting for a valid graph id…');
        return;
      }

      const url = `${base}/graphs/${encodeURIComponent(effectiveGraphId)}/degree_distribution`;
      const res = await fetch(url, {
        cache: 'no-store',
        headers: buildFaimHeaders(),
        signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}${text ? `: ${text}` : ''}`);
      }

      const body = await res.json();

      let buckets: DegreeBucket[] = [];

      if (Array.isArray(body)) {
        buckets = body
          .map((b: any) => ({
            degree: Number(b.degree ?? b.k ?? 0),
            count: Number(b.count ?? b.n ?? 0),
          }))
          .filter((b: DegreeBucket) => Number.isFinite(b.degree) && Number.isFinite(b.count));
      } else if (Array.isArray((body as any)?.buckets)) {
        buckets = (body as any).buckets
          .map((b: any) => ({
            degree: Number(b.degree ?? b.k ?? 0),
            count: Number(b.count ?? b.n ?? 0),
          }))
          .filter((b: DegreeBucket) => Number.isFinite(b.degree) && Number.isFinite(b.count));
      } else if (body && typeof body === 'object') {
        buckets = Object.entries(body as Record<string, unknown>)
          .map(([k, v]) => ({
            degree: Number(k),
            count: Number(v),
          }))
          .filter((b: DegreeBucket) => Number.isFinite(b.degree) && Number.isFinite(b.count));
      }

      buckets.sort((a, b) => a.degree - b.degree);

      if (!cancelled) setDegreeBuckets(buckets);
    }

    async function loadClusters(signal: AbortSignal) {
      setCluError(null);

      if (!base) {
        setClusters([]);
        setCluError('Analytics disabled: API base is missing.');
        return;
      }

      if (!effectiveGraphId) {
        setClusters([]);
        setCluError('Waiting for a valid graph id…');
        return;
      }

      const url = `${base}/graphs/${encodeURIComponent(effectiveGraphId)}/cluster_map?clusters=16`;
      const res = await fetch(url, {
        cache: 'no-store',
        headers: buildFaimHeaders(),
        signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}${text ? `: ${text}` : ''}`);
      }

      const body = await res.json();

      let stats: ClusterStat[] = [];

      if (Array.isArray((body as any)?.clusters)) {
        stats = (body as any).clusters
          .map((c: any) => ({
            cluster_id: Number(c.cluster_id ?? c.id ?? 0),
            count: Number(c.count ?? c.size ?? 0),
          }))
          .filter((c: ClusterStat) => Number.isFinite(c.cluster_id) && Number.isFinite(c.count));
      } else if (Array.isArray(body)) {
        // If backend returns node list with cluster_id, summarize it.
        const counts = new Map<number, number>();
        for (const item of body as any[]) {
          const cid = Number(item.cluster_id ?? item.cluster ?? NaN);
          if (!Number.isFinite(cid)) continue;
          counts.set(cid, (counts.get(cid) ?? 0) + 1);
        }
        stats = Array.from(counts.entries()).map(([cluster_id, count]) => ({ cluster_id, count }));
      } else if (body && typeof body === 'object') {
        stats = Object.entries(body as Record<string, unknown>)
          .map(([k, v]) => ({
            cluster_id: Number(k),
            count: Number(v),
          }))
          .filter((c: ClusterStat) => Number.isFinite(c.cluster_id) && Number.isFinite(c.count));
      }

      stats.sort((a, b) => a.cluster_id - b.cluster_id);

      if (!cancelled) setClusters(stats);
    }

    async function loadAll() {
      const controller = new AbortController();

      try {
        setLoading(true);
        await Promise.allSettled([loadDegree(controller.signal), loadClusters(controller.signal)]);
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
          '--mx': '52%',
          '--my': '28%',
          '--gvis': '0',
        } as CSSProperties
      }
      className={[
        'group relative overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4 text-xs',
        'ring-1 ring-inset ring-cyan-500/10',
        'transition duration-200 hover:border-cyan-500/35',
        'shadow-[0_0_0_1px_rgba(15,23,42,0.55),0_18px_70px_-40px_rgba(0,0,0,0.85)]',
        "before:content-[''] before:pointer-events-none before:absolute before:inset-0",
        "after:content-[''] after:pointer-events-none after:absolute after:inset-0",
        'before:[background:radial-gradient(620px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.11),transparent_66%)]',
        'before:opacity-[var(--gvis)]',
        'after:[background:radial-gradient(460px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.09),transparent_70%)]',
        'after:opacity-[var(--gvis)]',
      ].join(' ')}
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />

      <div className="relative z-[1]">
        <header className="mb-2 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-semibold text-slate-100">Graph analytics</h2>
            <p className="text-[11px] text-slate-400">
              Degree distribution and prototype cluster map.
            </p>
          </div>
          {loading && <span className="text-[10px] text-slate-500">Loading…</span>}
        </header>

        <div className="grid gap-3 md:grid-cols-2">
          {/* Degree distribution */}
          <div>
            <h3 className="mb-1 text-[11px] font-semibold text-slate-200">Degree distribution</h3>

            {degError ? (
              <p className="rounded border border-red-900/50 bg-red-950/40 px-2 py-1 text-[11px] text-red-100">
                {degError}
              </p>
            ) : degreeBuckets.length === 0 ? (
              <p className="rounded border border-dashed border-slate-700 bg-slate-950/60 px-2 py-3 text-[11px] text-slate-500">
                No degree data yet. Once the backend exposes{' '}
                <code className="font-mono text-[10px]">degree_distribution</code>, a histogram will
                appear here.
              </p>
            ) : (
              <div className="h-32 rounded bg-slate-950/80 p-2">
                <svg viewBox="0 0 220 80" className="h-full w-full">
                  {degreeBuckets.map((b, i) => {
                    const barWidth = 220 / Math.max(degreeBuckets.length, 1);
                    const x = i * barWidth + 2;
                    const ratio = maxCount > 0 ? b.count / maxCount : 0;
                    const height = ratio * 70;
                    const y = 78 - height;
                    return (
                      <g key={b.degree}>
                        <rect
                          x={x}
                          y={y}
                          width={barWidth - 4}
                          height={height}
                          rx={2}
                          className="fill-cyan-500/70"
                        />
                      </g>
                    );
                  })}
                </svg>
                <p className="mt-1 text-[10px] text-slate-500">
                  Each bar shows how many nodes have a given degree (parents + children).
                </p>
              </div>
            )}
          </div>

          {/* Cluster map */}
          <div>
            <h3 className="mb-1 text-[11px] font-semibold text-slate-200">
              Cluster map (prototype)
            </h3>

            {cluError ? (
              <p className="rounded border border-red-900/50 bg-red-950/40 px-2 py-1 text-[11px] text-red-100">
                {cluError}
              </p>
            ) : clusters.length === 0 ? (
              <p className="rounded border border-dashed border-slate-700 bg-slate-950/60 px-2 py-3 text-[11px] text-slate-500">
                No cluster data yet. Once{' '}
                <code className="font-mono text-[10px]">cluster_map</code> is wired, cluster sizes
                will appear here.
              </p>
            ) : (
              <ul className="space-y-1 text-[11px] text-slate-200">
                {clusters.map((c) => (
                  <li key={c.cluster_id}>
                    <GlowRow>
                      <div className="flex items-center justify-between">
                        <span>Cluster {c.cluster_id}</span>
                        <span className="text-slate-300">
                          {c.count} node{c.count === 1 ? '' : 's'}
                        </span>
                      </div>
                    </GlowRow>
                  </li>
                ))}
              </ul>
            )}

            <p className="mt-1 text-[10px] text-slate-500">
              Later, FIG nodes can be colored by cluster id for quick visual structure.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default GraphAnalyticsPanel;
