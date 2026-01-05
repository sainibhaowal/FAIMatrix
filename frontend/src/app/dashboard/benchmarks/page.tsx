// src/app/benchmarks/page.tsx
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  API_BASE_URL,
  DEFAULT_GRAPH_ID,
  buildFaimHeaders,
  fetchBenchmarks,
  getUniverseGraphId,
  type BenchmarkPoint,
} from "@/lib/api";
import {
  useFaimStream,
  type BenchPoint,
  type MetricsEvent,
} from "@/lib/realtime";
import { useUserIds } from "@/contexts/UserContext";

type Run = {
  id: string;
  timestamp?: string | null;
  nodes?: number | null;
  cr?: number | null;
  redundancy?: number | null;
  drift?: number | null;
  retrieve_p50_ms?: number | null;
  retrieve_p95_ms?: number | null;
};

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

/**
 * Neon “spotlight” card:
 * - cursor-follow spotlight on hover
 * - DOES NOT reset on mouse leave (stays at last position)
 * - subtle cyan border + glow
 */
function GlowCard({
  children,
  className = "",
  intensity = 0.35,
}: {
  children: React.ReactNode;
  className?: string;
  intensity?: number;
}) {
  const o = String(clamp01(intensity));

  return (
    <div
      onMouseMove={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        const r = el.getBoundingClientRect();
        const x = ((e.clientX - r.left) / r.width) * 100;
        const y = ((e.clientY - r.top) / r.height) * 100;
        // Smooth + no re-render: write CSS vars directly
        el.style.setProperty("--gx", `${x.toFixed(2)}%`);
        el.style.setProperty("--gy", `${y.toFixed(2)}%`);
      }}
      style={
        {
          ["--gx" as any]: "50%",
          ["--gy" as any]: "50%",
          ["--go" as any]: o,
        } as React.CSSProperties
      }
      className={[
        "relative overflow-hidden rounded-2xl border",
        "border-cyan-300/10 bg-slate-950/60",
        "shadow-[0_0_0_1px_rgba(34,211,238,0.10),0_0_30px_rgba(34,211,238,0.05)]",
        "transition-transform duration-200 will-change-transform hover:-translate-y-[1px]",
        "before:absolute before:inset-0 before:pointer-events-none",
        "before:bg-[linear-gradient(180deg,rgba(34,211,238,0.10),transparent_45%,transparent)]",
        "after:absolute after:inset-0 after:pointer-events-none",
        "after:opacity-100 after:transition-opacity after:duration-200",
        // smaller + softer spotlight
        "after:bg-[radial-gradient(220px_circle_at_var(--gx)_var(--gy),rgba(34,211,238,calc(var(--go)*0.12)),transparent_62%)]",
        "ring-1 ring-white/5",
        className,
      ].join(" ")}
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />
      <div className="relative p-4">{children}</div>
    </div>
  );
}

function fmt(n?: number | null, digits = 2) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function fmtInt(n?: number | null) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return Math.round(n).toLocaleString();
}

function toRun(p: BenchmarkPoint | BenchPoint, idx: number): Run {
  const latency: any = (p as any).latency ?? {};
  return {
    id: `${(p as any).timestamp ?? ""}-${idx}`,
    timestamp: (p as any).timestamp ?? null,
    nodes: (p as any).nodes ?? null,
    cr: (p as any).cr ?? (p as any).compression_ratio ?? null,
    redundancy: (p as any).redundancy ?? null,
    drift: (p as any).drift ?? null,
    retrieve_p50_ms:
      latency.retrieve_p50_ms ?? (p as any).retrieve_p50_ms ?? null,
    retrieve_p95_ms:
      latency.retrieve_p95_ms ?? (p as any).retrieve_p95_ms ?? null,
  };
}

/**
 * Beautiful neon dropdown (replaces native <select> popup).
 * NOTE: must be top-level (not inside BenchmarksPage) to avoid hook nesting issues.
 */
function NeonDropdown<T extends string>({
  label,
  value,
  options,
  onChange,
  minWidthClass = "min-w-[110px]",
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  minWidthClass?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  return (
    <div
      ref={rootRef}
      className="relative flex items-center gap-2 rounded-xl border border-cyan-300/10 bg-slate-950/60 px-3 py-2
                 transition-all duration-200 active:scale-[0.98]"
    >
      <span className="text-slate-400">{label}</span>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={[
          minWidthClass,
          "inline-flex items-center justify-between gap-2 rounded-md border border-slate-800/80 bg-slate-950/80",
          "px-2 py-1 text-slate-100 outline-none",
          "focus:ring-1 focus:ring-cyan-500/60",
          "hover:border-cyan-400/25",
        ].join(" ")}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="truncate">
          {options.find((o) => o.value === value)?.label ?? value}
        </span>
        <span className="text-slate-400">▾</span>
      </button>

      <div
        className={[
          "absolute right-0 top-[calc(100%+8px)] z-50",
          "w-[240px] overflow-hidden rounded-xl border border-cyan-300/15",
          "bg-slate-950/90 backdrop-blur-md",
          "shadow-[0_0_0_1px_rgba(34,211,238,0.10),0_30px_90px_-40px_rgba(0,0,0,0.9)]",
          "transition-all duration-150 origin-top-right",
          open
            ? "scale-100 opacity-100 translate-y-0"
            : "pointer-events-none scale-[0.98] opacity-0 -translate-y-1",
        ].join(" ")}
        role="listbox"
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(520px_circle_at_30%_0%,rgba(34,211,238,0.10),transparent_60%)]" />

        <div className="relative">
          {options.map((opt) => {
            const active = opt.value === value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
                className={[
                  "w-full text-left px-3 py-2 text-sm",
                  "transition-colors",
                  active
                    ? "bg-cyan-500/10 text-cyan-200"
                    : "text-slate-200 hover:bg-cyan-500/8 hover:text-slate-50",
                ].join(" ")}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function BenchmarksPage() {
  const defaultGraphId = DEFAULT_GRAPH_ID.startsWith("U:")
    ? DEFAULT_GRAPH_ID
    : "";
  const [graphId, setGraphId] = useState<string>(defaultGraphId);

  // SYNC WITH AUTH: Authoritative graph ID
  const { graphId: contextGraphId } = useUserIds();

  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);

  const [sortBy, setSortBy] = useState<"newest" | "nodes" | "cr" | "p95">(
    "newest",
  );
  const [limit, setLimit] = useState<"10" | "20" | "50" | "all">("20");

  const runTimerRef = useRef<number | null>(null);
  const runStopRef = useRef<number | null>(null);

  // kept (even if unused now) — no functional damage
  const [sortFlash, setSortFlash] = useState(false);
  const [limitFlash, setLimitFlash] = useState(false);
  void sortFlash;
  void limitFlash;

  // Sync with UserContext
  useEffect(() => {
    if (contextGraphId && contextGraphId.startsWith("U:")) {
      setGraphId(contextGraphId);
    } else {
      // Fallback
      const u = getUniverseGraphId();
      if (u && u.startsWith("U:")) setGraphId(u);
    }
  }, [contextGraphId]);

  // Handle cross-tab updates (optional fallback)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onStorage = (e: StorageEvent) => {
      if (!e.key) return;
      if (e.key.includes("graph_id")) {
        const u = getUniverseGraphId();
        if (u && u.startsWith("U:")) setGraphId(u);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => {
    let alive = true;

    (async () => {
      try {
        setError(null);
        if (!graphId) return;
        const pts = await fetchBenchmarks(graphId || undefined);
        if (!alive) return;
        setRuns(pts.map((p, i) => toRun(p, i)));
      } catch (e: any) {
        if (!alive) return;
        setError(e?.message ?? "Failed to load benchmarks.");
      }
    })();

    return () => {
      alive = false;
    };
  }, [graphId]);

  useFaimStream(graphId || undefined, {
    onBenchPoint: (p: BenchPoint) => {
      setRuns((prev) => {
        const next = [...prev, toRun(p, prev.length)];
        if (next.length > 500) return next.slice(next.length - 500);
        return next;
      });
    },
    onError: (e: any) => {
      const msg =
        typeof e === "string"
          ? e
          : ((e?.message as string | undefined) ?? "Stream error.");
      setError(msg);
    },
  });

  useEffect(() => {
    return () => {
      if (runTimerRef.current) window.clearInterval(runTimerRef.current);
      if (runStopRef.current) window.clearTimeout(runStopRef.current);
    };
  }, []);

  const runSnapshotOnce = async () => {
    if (!graphId) throw new Error("Universe graph_id not ready.");

    const res = await fetch(
      `${API_BASE_URL}/benchmarks/${encodeURIComponent(graphId)}/snapshot`,
      {
        method: "POST",
        headers: buildFaimHeaders(),
      },
    );

    if (!res.ok)
      throw new Error(`Benchmark snapshot failed: HTTP ${res.status}`);
    const point = (await res.json()) as BenchmarkPoint;
    setRuns((prev) => [...prev, toRun(point, prev.length)]);
    return point;
  };

  const stopRun = () => {
    if (runTimerRef.current) window.clearInterval(runTimerRef.current);
    if (runStopRef.current) window.clearTimeout(runStopRef.current);
    runTimerRef.current = null;
    runStopRef.current = null;
    setRunStatus(null);
  };

  const runSchedule = (
    label: string,
    intervalMs: number,
    totalMs?: number,
    count?: number,
  ) => {
    stopRun();
    setError(null);
    setRunStatus(label);

    let remaining = typeof count === "number" ? Math.max(1, count) : null;

    const tick = async () => {
      try {
        await runSnapshotOnce();
        if (remaining !== null) {
          remaining -= 1;
          if (remaining <= 0) stopRun();
        }
      } catch (e: any) {
        setError(e?.message ?? "Benchmark run failed.");
        stopRun();
      }
    };

    void tick();

    runTimerRef.current = window.setInterval(() => void tick(), intervalMs);

    if (typeof totalMs === "number" && Number.isFinite(totalMs)) {
      runStopRef.current = window.setTimeout(() => stopRun(), totalMs);
    }
  };

  const sortedFiltered = useMemo(() => {
    const copy = [...runs];
    copy.sort((a, b) => {
      if (sortBy === "newest")
        return (b.timestamp ?? "").localeCompare(a.timestamp ?? "");
      if (sortBy === "nodes") return (b.nodes ?? 0) - (a.nodes ?? 0);
      if (sortBy === "cr") return (b.cr ?? 0) - (a.cr ?? 0);
      return (b.retrieve_p95_ms ?? 0) - (a.retrieve_p95_ms ?? 0);
    });

    if (limit === "10") return copy.slice(0, 10);
    if (limit === "20") return copy.slice(0, 20);
    if (limit === "50") return copy.slice(0, 50);
    return copy;
  }, [runs, sortBy, limit]);

  const sparkline = useMemo(() => {
    const values = sortedFiltered
      .map((r) =>
        typeof r.retrieve_p95_ms === "number" ? r.retrieve_p95_ms : null,
      )
      .filter((v): v is number => v !== null);

    if (!values.length) return null;

    const width = 520;
    const height = 80;
    const pad = 8;

    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = Math.max(1e-9, max - min);

    const pts = values.map((v, i) => {
      const x = pad + (i / Math.max(1, values.length - 1)) * (width - pad * 2);
      const y = height - pad - ((v - min) / span) * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="h-20 w-full">
        <polyline
          points={pts.join(" ")}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="text-cyan-300/70"
        />
        <polyline
          points={pts.join(" ")}
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          className="text-cyan-400/10"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }, [sortedFiltered]);

  const latest = useMemo(() => {
    if (!runs.length) return null;
    const copy = [...runs].sort((a, b) =>
      (b.timestamp ?? "").localeCompare(a.timestamp ?? ""),
    );
    return copy[0] ?? null;
  }, [runs]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-50">Benchmarks</h1>
          <div className="text-sm text-slate-400">
            Live + historical CR/R/Drift/Latency for{" "}
            <span className="text-cyan-300">{graphId || "—"}</span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-2 text-xs">
          <NeonDropdown
            label="Sort"
            value={sortBy}
            onChange={(v) => setSortBy(v)}
            options={[
              { value: "newest", label: "Newest" },
              { value: "nodes", label: "Nodes" },
              { value: "cr", label: "CR" },
              { value: "p95", label: "p95" },
            ]}
            minWidthClass="min-w-[110px]"
          />

          <NeonDropdown
            label="Limit"
            value={limit}
            onChange={(v) => setLimit(v)}
            options={[
              { value: "10", label: "10" },
              { value: "20", label: "20" },
              { value: "50", label: "50" },
              { value: "all", label: "All" },
            ]}
            minWidthClass="min-w-[84px]"
          />
        </div>
      </div>

      <GlowCard className="border-cyan-400/15">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-slate-400">
              Run Benchmarks
            </div>
            <div className="mt-1 text-sm text-slate-200">
              {runStatus ? `Running: ${runStatus}` : "Ready to run snapshots."}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px]">
            <button
              type="button"
              onClick={() => runSchedule("Single snapshot", 0, undefined, 1)}
              disabled={!graphId}
              className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 font-semibold uppercase tracking-widest text-cyan-200 transition hover:border-cyan-300/60 hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Run Once
            </button>
            <button
              type="button"
              onClick={() => runSchedule("Burst x10 (1s)", 1000, undefined, 10)}
              disabled={!graphId}
              className="rounded-full border border-slate-700/70 bg-slate-950/60 px-3 py-2 font-semibold uppercase tracking-widest text-slate-200 transition hover:border-cyan-300/40 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Burst x10
            </button>
            <button
              type="button"
              onClick={() => runSchedule("1 min (5s)", 5000, 60_000)}
              disabled={!graphId}
              className="rounded-full border border-slate-700/70 bg-slate-950/60 px-3 py-2 font-semibold uppercase tracking-widest text-slate-200 transition hover:border-cyan-300/40 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              1 Min
            </button>
            <button
              type="button"
              onClick={() => runSchedule("5 min (10s)", 10_000, 300_000)}
              disabled={!graphId}
              className="rounded-full border border-slate-700/70 bg-slate-950/60 px-3 py-2 font-semibold uppercase tracking-widest text-slate-200 transition hover:border-cyan-300/40 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              5 Min
            </button>
            <button
              type="button"
              onClick={() => runSchedule("15 min (30s)", 30_000, 900_000)}
              disabled={!graphId}
              className="rounded-full border border-slate-700/70 bg-slate-950/60 px-3 py-2 font-semibold uppercase tracking-widest text-slate-200 transition hover:border-cyan-300/40 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              15 Min
            </button>
            <button
              type="button"
              onClick={stopRun}
              className="rounded-full border border-rose-400/30 bg-rose-500/10 px-3 py-2 font-semibold uppercase tracking-widest text-rose-200 transition hover:border-rose-300/60 hover:bg-rose-500/20"
            >
              Stop
            </button>
          </div>
        </div>
      </GlowCard>

      {error && (
        <GlowCard intensity={0.22} className="border-rose-300/15">
          <div className="text-sm text-rose-200">{error}</div>
        </GlowCard>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <GlowCard>
          <div className="text-[11px] uppercase tracking-widest text-slate-400">
            Latest
          </div>
          <div className="mt-2 text-sm text-slate-100">
            {latest?.timestamp ? (
              <div className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.6)]" />
                <span className="font-mono text-xs text-slate-300">
                  {latest.timestamp}
                </span>
              </div>
            ) : (
              "—"
            )}
          </div>
        </GlowCard>

        <GlowCard>
          <div className="text-[11px] uppercase tracking-widest text-slate-400">
            Nodes
          </div>
          <div className="mt-2 text-2xl font-semibold text-slate-50">
            {fmtInt(latest?.nodes)}
          </div>
        </GlowCard>

        <GlowCard>
          <div className="text-[11px] uppercase tracking-widest text-slate-400">
            Latency p95
          </div>
          <div className="mt-2 text-2xl font-semibold text-slate-50">
            {fmt(latest?.retrieve_p95_ms, 1)}{" "}
            <span className="text-sm text-slate-400">ms</span>
          </div>
        </GlowCard>
      </div>

      <GlowCard className="p-0">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-slate-50">
              p95 Latency Sparkline
            </div>
            <div className="text-xs text-slate-400">
              Scroll your mouse over the card to “paint” the glow.
            </div>
          </div>
          <div className="text-xs text-slate-400">
            points:{" "}
            <span className="text-slate-200">{sortedFiltered.length}</span>
          </div>
        </div>
        <div className="mt-3">
          {sparkline ?? (
            <div className="text-sm text-slate-400">No data yet.</div>
          )}
        </div>
      </GlowCard>

      <GlowCard>
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-medium text-slate-50">Runs</div>
          <div className="text-xs text-slate-400">
            Hover any row area: glow follows + stays.
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-slate-400">
              <tr className="border-b border-cyan-300/10">
                <th className="py-2 pr-3 font-medium">Timestamp</th>
                <th className="py-2 pr-3 font-medium">Nodes</th>
                <th className="py-2 pr-3 font-medium">CR</th>
                <th className="py-2 pr-3 font-medium">R</th>
                <th className="py-2 pr-3 font-medium">Drift</th>
                <th className="py-2 pr-3 font-medium">p50</th>
                <th className="py-2 pr-0 font-medium">p95</th>
              </tr>
            </thead>
            <tbody className="text-slate-200">
              {sortedFiltered.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-slate-800/50 hover:bg-cyan-500/5"
                >
                  <td className="py-2 pr-3 font-mono text-[11px] text-slate-300">
                    {r.timestamp ?? "—"}
                  </td>
                  <td className="py-2 pr-3">{fmtInt(r.nodes)}</td>
                  <td className="py-2 pr-3">{fmt(r.cr, 2)}</td>
                  <td className="py-2 pr-3">{fmt(r.redundancy, 3)}</td>
                  <td className="py-2 pr-3">{fmt(r.drift, 3)}</td>
                  <td className="py-2 pr-3">{fmt(r.retrieve_p50_ms, 1)} ms</td>
                  <td className="py-2 pr-0">{fmt(r.retrieve_p95_ms, 1)} ms</td>
                </tr>
              ))}
              {!sortedFiltered.length && (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-400">
                    No benchmark runs yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </GlowCard>
    </div>
  );
}
