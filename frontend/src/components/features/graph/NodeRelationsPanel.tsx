"use client";

import * as React from "react";
import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, buildFaimHeaders } from "@/lib/api";

type TabKey = "memory" | "neighbors" | "lineage" | "vector";

type Neighbor = {
  id: string;
  label?: string;
  distance?: number;
};

type LineageItem = {
  id: string;
  label?: string;
};

type VectorStats = {
  norm?: number;
  mean?: number;
  std?: number;
  min?: number;
  max?: number;
  [key: string]: unknown;
};

type MemoryStats = {
  totalNodes?: number | null;
  payloadChars?: number | null;
  payloadLines?: number | null;
  preview?: string | null;
};

interface NodeRelationsPanelProps {
  nodeId: string | null;
  graphId?: string; // MUST be the real Universe ID (U:...) for the current user
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

/**
 * Sticky glow for panel + list items:
 * - updates CSS vars on pointer move capture
 * - does NOT reset on leave (sticky)
 * - controlled intensity (avoid "too much glow")
 */
function useStickyGlowVars(intensity = 0.22) {
  const ref = useRef<HTMLElement | null>(null);

  const onPointerMoveCapture = (e: React.PointerEvent<HTMLElement>) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;
    el.style.setProperty("--mx", `${x.toFixed(2)}%`);
    el.style.setProperty("--my", `${y.toFixed(2)}%`);
    el.style.setProperty("--gvis", String(intensity));
  };

  const onPointerLeave = () => {
    // sticky: do nothing
  };

  return { ref, onPointerMoveCapture, onPointerLeave };
}

export function NodeRelationsPanel({
  nodeId,
  graphId,
}: NodeRelationsPanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("neighbors");

  const [neighbors, setNeighbors] = useState<Neighbor[]>([]);
  const [lineage, setLineage] = useState<LineageItem[]>([]);
  const [vectorStats, setVectorStats] = useState<VectorStats | null>(null);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // IMPORTANT: production rule — do NOT fall back to MAIN/demo.
  const effectiveGraphId = (graphId ?? "").trim();

  useEffect(() => {
    // If universe id not ready yet, do nothing.
    if (!effectiveGraphId) {
      setNeighbors([]);
      setLineage([]);
      setVectorStats(null);
      setMemoryStats(null);
      setError(null);
      setLoading(false);
      return;
    }

    if (!nodeId) {
      setNeighbors([]);
      setLineage([]);
      setVectorStats(null);
      setMemoryStats(null);
      setError(null);
      setLoading(false);
      return;
    }

    const currentNodeId = nodeId;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        if (activeTab === "memory") {
          const [countRes, detailRes] = await Promise.all([
            fetch(
              `${API_BASE_URL}/graphs/${encodeURIComponent(
                effectiveGraphId,
              )}/node_count`,
              {
                cache: "no-store",
                headers: buildFaimHeaders(),
              },
            ),
            fetch(
              `${API_BASE_URL}/graphs/${encodeURIComponent(
                effectiveGraphId,
              )}/node/${encodeURIComponent(currentNodeId)}`,
              {
                cache: "no-store",
                headers: buildFaimHeaders(),
              },
            ),
          ]);

          let totalNodes: number | null = null;
          let payloadChars: number | null = null;
          let payloadLines: number | null = null;
          let preview: string | null = null;

          if (countRes.ok) {
            const data = (await countRes.json()) as any;
            if (typeof data?.node_count === "number")
              totalNodes = data.node_count;
          }

          if (detailRes.ok) {
            const data = (await detailRes.json()) as any;
            const payload =
              typeof data?.payload === "string" ? data.payload : "";
            preview = typeof data?.preview === "string" ? data.preview : null;
            if (payload) {
              payloadChars = payload.length;
              payloadLines = payload.split("\n").length;
            } else if (preview) {
              payloadChars = preview.length;
              payloadLines = preview.split("\n").length;
            }
          }

          if (!cancelled) {
            setMemoryStats({
              totalNodes,
              payloadChars,
              payloadLines,
              preview,
            });
          }
        } else if (activeTab === "neighbors") {
          const res = await fetch(
            `${API_BASE_URL}/graphs/${encodeURIComponent(
              effectiveGraphId,
            )}/node/${encodeURIComponent(currentNodeId)}/neighbors?k=10`,
            {
              cache: "no-store",
              headers: buildFaimHeaders(),
            },
          );

          if (!res.ok) throw new Error(`neighbors HTTP ${res.status}`);
          const data = (await res.json()) as any;
          const arr = Array.isArray(data) ? data : (data.neighbors ?? []);

          if (!cancelled) {
            setNeighbors(
              arr
                .map((n: any) => {
                  if (typeof n === "string" || typeof n === "number") {
                    return { id: String(n) };
                  }
                  return {
                    id: String(n.id ?? n.node_id ?? ""),
                    label: n.label,
                    distance:
                      typeof n.distance === "number"
                        ? n.distance
                        : typeof n.score === "number"
                          ? n.score
                          : undefined,
                  };
                })
                .filter((x: Neighbor) => x.id),
            );
          }
        } else if (activeTab === "lineage") {
          const res = await fetch(
            `${API_BASE_URL}/graphs/${encodeURIComponent(
              effectiveGraphId,
            )}/node/${encodeURIComponent(currentNodeId)}/lineage?depth=10`,
            {
              cache: "no-store",
              headers: buildFaimHeaders(),
            },
          );

          if (!res.ok) throw new Error(`lineage HTTP ${res.status}`);
          const data = (await res.json()) as any;
          const arr = Array.isArray(data) ? data : (data.lineage ?? []);

          if (!cancelled) {
            setLineage(
              arr
                .map((n: any) => {
                  if (typeof n === "string" || typeof n === "number") {
                    return { id: String(n) };
                  }
                  return {
                    id: String(n.id ?? n.node_id ?? ""),
                    label: n.label,
                  };
                })
                .filter((x: LineageItem) => x.id),
            );
          }
        } else if (activeTab === "vector") {
          const res = await fetch(
            `${API_BASE_URL}/graphs/${encodeURIComponent(
              effectiveGraphId,
            )}/node/${encodeURIComponent(currentNodeId)}/vector_stats`,
            {
              cache: "no-store",
              headers: buildFaimHeaders(),
            },
          );

          if (!res.ok) throw new Error(`vector_stats HTTP ${res.status}`);
          const data = (await res.json()) as any;
          if (!cancelled) setVectorStats(data as VectorStats);
        }
      } catch (err: any) {
        if (!cancelled) {
          console.warn("NodeRelationsPanel load failed", err);
          setError("Unable to load data for this node.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [nodeId, effectiveGraphId, activeTab]);

  const glow = useStickyGlowVars(0.2);

  return (
    <aside
      ref={glow.ref as React.RefObject<HTMLElement>}
      onPointerMoveCapture={glow.onPointerMoveCapture}
      onPointerLeave={glow.onPointerLeave}
      style={
        {
          "--mx": "55%",
          "--my": "22%",
          "--gvis": "0",
        } as React.CSSProperties
      }
      className={[
        "group relative h-full overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4 text-xs",
        "ring-1 ring-inset ring-cyan-500/10",
        "shadow-[0_0_0_1px_rgba(15,23,42,0.55),0_18px_70px_-40px_rgba(0,0,0,0.85)]",
        "transition duration-200 hover:border-cyan-500/35",
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
        <header className="mb-3 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-semibold text-slate-100">
              Memory / Neighbors / Lineage / Vector
            </h2>
            <p className="text-[11px] text-slate-400">
              Memory totals, similar nodes, inheritance chain, and vector
              statistics for the selected node.
            </p>
          </div>
          <TabSwitch active={activeTab} onChange={setActiveTab} />
        </header>

        {!effectiveGraphId ? (
          <p className="text-[11px] text-slate-500">
            Waiting for your Universe ID (U:...) to be resolved.
          </p>
        ) : !nodeId ? (
          <p className="text-[11px] text-slate-500">
            Select a node in the FIG to see memory, neighbors, lineage and
            vector stats.
          </p>
        ) : loading ? (
          <p className="text-[11px] text-slate-400">Loading…</p>
        ) : error ? (
          <p className="text-[11px] text-rose-400">{error}</p>
        ) : activeTab === "memory" ? (
          <MemoryStatsView stats={memoryStats} />
        ) : activeTab === "neighbors" ? (
          <NeighborsList neighbors={neighbors} />
        ) : activeTab === "lineage" ? (
          <LineageList lineage={lineage} />
        ) : (
          <VectorStatsView stats={vectorStats} />
        )}
      </div>
    </aside>
  );
}

function TabSwitch({
  active,
  onChange,
}: {
  active: TabKey;
  onChange: (t: TabKey) => void;
}) {
  const base = "px-2 py-0.5 rounded-full text-[10px] transition-colors";
  return (
    <div className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900/80 p-0.5 text-[10px]">
      <button
        type="button"
        className={
          active === "memory"
            ? `${base} bg-cyan-500 text-slate-950`
            : `${base} text-slate-300 hover:bg-slate-800`
        }
        onClick={() => onChange("memory")}
      >
        Memory
      </button>
      <button
        type="button"
        className={
          active === "neighbors"
            ? `${base} bg-cyan-500 text-slate-950`
            : `${base} text-slate-300 hover:bg-slate-800`
        }
        onClick={() => onChange("neighbors")}
      >
        Neighbors
      </button>
      <button
        type="button"
        className={
          active === "lineage"
            ? `${base} bg-cyan-500 text-slate-950`
            : `${base} text-slate-300 hover:bg-slate-800`
        }
        onClick={() => onChange("lineage")}
      >
        Lineage
      </button>
      <button
        type="button"
        className={
          active === "vector"
            ? `${base} bg-cyan-500 text-slate-950`
            : `${base} text-slate-300 hover:bg-slate-800`
        }
        onClick={() => onChange("vector")}
      >
        Vector
      </button>
    </div>
  );
}

/** List-item mini glow */
function GlowRow({ children }: { children: React.ReactNode }) {
  const glow = useStickyGlowVars(0.16);
  return (
    <div
      ref={glow.ref as React.RefObject<HTMLDivElement>}
      onPointerMoveCapture={glow.onPointerMoveCapture as any}
      onPointerLeave={glow.onPointerLeave}
      style={
        {
          "--mx": "50%",
          "--my": "40%",
          "--gvis": "0",
        } as React.CSSProperties
      }
      className={[
        "relative overflow-hidden rounded-md border border-slate-800/80 bg-slate-900/70",
        "transition hover:border-cyan-500/30",
        "before:content-[''] before:pointer-events-none before:absolute before:inset-0",
        "before:[background:radial-gradient(420px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.10),transparent_66%)]",
        "before:opacity-[var(--gvis)]",
      ].join(" ")}
    >
      <div className="relative z-[1]">{children}</div>
    </div>
  );
}

function NeighborsList({ neighbors }: { neighbors: Neighbor[] }) {
  if (!neighbors || neighbors.length === 0) {
    return <p className="text-[11px] text-slate-500">No neighbors found.</p>;
  }

  return (
    <ul className="space-y-2">
      {neighbors.map((n) => (
        <li key={n.id}>
          <GlowRow>
            <div className="flex items-center justify-between gap-2 px-2 py-1">
              <div className="truncate text-[11px] text-slate-100">
                {n.label || n.id}
              </div>
              {typeof n.distance === "number" && (
                <span className="shrink-0 rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                  d = {n.distance.toFixed(3)}
                </span>
              )}
            </div>
          </GlowRow>
        </li>
      ))}
    </ul>
  );
}

function MemoryStatsView({ stats }: { stats: MemoryStats | null }) {
  if (!stats) {
    return (
      <p className="text-[11px] text-slate-500">No memory data available.</p>
    );
  }

  return (
    <div className="space-y-3 text-[11px] text-slate-200">
      <div className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900/70 px-2 py-1">
        <span className="text-slate-400">Total memories</span>
        <span className="font-semibold text-slate-100">
          {stats.totalNodes ?? "—"}
        </span>
      </div>
      <div className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900/70 px-2 py-1">
        <span className="text-slate-400">Payload size</span>
        <span className="font-semibold text-slate-100">
          {stats.payloadChars ?? "—"} chars
        </span>
      </div>
      <div className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900/70 px-2 py-1">
        <span className="text-slate-400">Payload lines</span>
        <span className="font-semibold text-slate-100">
          {stats.payloadLines ?? "—"}
        </span>
      </div>
      {stats.preview && (
        <div className="rounded-md border border-slate-800 bg-slate-900/70 px-2 py-1 text-[10px] text-slate-300">
          {stats.preview}
        </div>
      )}
    </div>
  );
}

function LineageList({ lineage }: { lineage: LineageItem[] }) {
  if (!lineage || lineage.length === 0) {
    return <p className="text-[11px] text-slate-500">No lineage found.</p>;
  }

  return (
    <ol className="space-y-2">
      {lineage.map((n, idx) => (
        <li key={n.id}>
          <GlowRow>
            <div className="flex items-start gap-2 px-2 py-1">
              <div className="mt-0.5 h-2 w-2 rounded-full bg-cyan-500" />
              <div>
                <div className="text-[11px] text-slate-100">
                  {n.label || n.id}
                </div>
                <div className="text-[10px] text-slate-500">{n.id}</div>
                {idx < lineage.length - 1 && (
                  <div className="ml-1 text-[10px] text-slate-600">
                    ↓ inherits from
                  </div>
                )}
              </div>
            </div>
          </GlowRow>
        </li>
      ))}
    </ol>
  );
}

function VectorStatsView({ stats }: { stats: VectorStats | null }) {
  if (!stats) {
    return (
      <p className="text-[11px] text-slate-500">
        No vector statistics available.
      </p>
    );
  }

  const entries: { key: keyof VectorStats; label: string }[] = [
    { key: "norm", label: "Norm" },
    { key: "mean", label: "Mean" },
    { key: "std", label: "Std" },
    { key: "min", label: "Min" },
    { key: "max", label: "Max" },
  ];

  const numericValues = entries
    .map((e) =>
      typeof stats[e.key] === "number" ? (stats[e.key] as number) : null,
    )
    .filter((v): v is number => v !== null);

  const globalMin = numericValues.length > 0 ? Math.min(...numericValues) : 0;
  const globalMax = numericValues.length > 0 ? Math.max(...numericValues) : 1;
  const span = globalMax - globalMin || 1;

  return (
    <div className="space-y-2">
      {entries.map(({ key, label }) => {
        const v = stats[key];
        if (typeof v !== "number") return null;

        const norm = (v - globalMin) / span;
        const widthPct = Math.max(4, Math.min(100, norm * 100));

        return (
          <div key={String(key)} className="space-y-1">
            <div className="flex items-center justify-between gap-2 text-[10px]">
              <span className="uppercase tracking-wide text-slate-500">
                {label}
              </span>
              <span className="text-slate-100">{v.toFixed(3)}</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-800">
              <div
                className="h-1.5 rounded-full bg-cyan-500"
                style={{ width: `${widthPct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default NodeRelationsPanel;
