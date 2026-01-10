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
} from "@/lib/realtime";
import { useUserIds } from "@/contexts/UserContext";
import { GlowCard } from "@/components/ui/GlowCard";
import { Select } from "@/components/ui/Select";
import { ChevronDown, ChevronUp, Activity, Database, Zap, Brain, GitMerge, Scissors, TrendingUp } from "lucide-react";

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

export default function BenchmarksPage() {
  const defaultGraphId = DEFAULT_GRAPH_ID.startsWith("U:")
    ? DEFAULT_GRAPH_ID
    : "";
  const [graphId, setGraphId] = useState<string>(defaultGraphId);
  const { graphId: contextGraphId } = useUserIds();

  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Evolution aggregate stats from /aggregate endpoint
  type AggregateStats = {
    prune_events: number;
    prune_rate_per_min: number;
    node_growth: number;
    node_growth_per_min: number;
  };
  const [aggregate, setAggregate] = useState<AggregateStats | null>(null);

  const [sortBy, setSortBy] = useState<string>("newest");
  const [limit, setLimit] = useState<string>("20");

  const runTimerRef = useRef<number | null>(null);
  const runStopRef = useRef<number | null>(null);

  // Sync with UserContext
  useEffect(() => {
    if (contextGraphId && contextGraphId.startsWith("U:")) {
      setGraphId(contextGraphId);
    } else {
      const u = getUniverseGraphId();
      if (u && u.startsWith("U:")) setGraphId(u);
    }
  }, [contextGraphId]);

  // Handle cross-tab updates
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
        
        // Fetch aggregate stats (prune/merge counts)
        try {
          const aggRes = await fetch(`${API_BASE_URL}/benchmarks/${encodeURIComponent(graphId)}/aggregate`, {
            headers: buildFaimHeaders(),
          });
          if (aggRes.ok && alive) {
            const agg = await aggRes.json();
            setAggregate({
              prune_events: agg.prune_events ?? 0,
              prune_rate_per_min: agg.prune_rate_per_min ?? 0,
              node_growth: agg.node_growth ?? 0,
              node_growth_per_min: agg.node_growth_per_min ?? 0,
            });
          }
        } catch { /* aggregate endpoint optional */ }
      } catch (e: any) {
        if (!alive) return;
        setError(e?.message ?? "Failed to load benchmarks.");
      }
    })();
    return () => { alive = false; };
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
      const msg = typeof e === "string" ? e : ((e?.message as string | undefined) ?? "Stream error.");
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
    const res = await fetch(`${API_BASE_URL}/benchmarks/${encodeURIComponent(graphId)}/snapshot`, {
      method: "POST",
      headers: buildFaimHeaders(),
    });
    if (!res.ok) throw new Error(`Benchmark snapshot failed: HTTP ${res.status}`);
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

  const runSchedule = (label: string, intervalMs: number, totalMs?: number, count?: number) => {
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
      if (sortBy === "newest") return (b.timestamp ?? "").localeCompare(a.timestamp ?? "");
      if (sortBy === "nodes") return (b.nodes ?? 0) - (a.nodes ?? 0);
      if (sortBy === "cr") return (b.cr ?? 0) - (a.cr ?? 0);
      return (b.retrieve_p95_ms ?? 0) - (a.retrieve_p95_ms ?? 0);
    });

    if (limit === "10") return copy.slice(0, 10);
    if (limit === "20") return copy.slice(0, 20);
    if (limit === "50") return copy.slice(0, 50);
    return copy;
  }, [runs, sortBy, limit]);

  const latest = useMemo(() => {
    if (!runs.length) return null;
    const copy = [...runs].sort((a, b) => (b.timestamp ?? "").localeCompare(a.timestamp ?? ""));
    return copy[0] ?? null;
  }, [runs]);

  // Derived Metrics for Brain Health
  const thinkingSpeed = latest?.retrieve_p95_ms; // ms
  const speedLabel = !thinkingSpeed ? "Unknown" : thinkingSpeed < 100 ? "Lightning" : thinkingSpeed < 300 ? "Healthy" : "Sluggish";
  const speedColor = !thinkingSpeed ? "text-slate-400" : thinkingSpeed < 100 ? "text-emerald-400" : thinkingSpeed < 300 ? "text-cyan-400" : "text-amber-400";
  
  const efficiency = latest?.cr ?? 0; // ratio
  const efficiencyLabel = efficiency > 1.5 ? "High" : efficiency > 1.0 ? "Normal" : "Low";

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-50 flex items-center gap-2">
            <Brain className="w-6 h-6 text-cyan-400" />
            Brain Health
          </h1>
          <div className="text-sm text-slate-400">
            Performance diagnostics for <span className="text-cyan-300 font-mono">{graphId?.slice(0,8)}...</span>
          </div>
        </div>
      </div>

      {/* Primary Health Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Metric 1: Thinking Speed */}
        <GlowCard className="border-cyan-400/20">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold mb-1">
                Thinking Speed
              </div>
              <div className={`text-3xl font-bold ${speedColor}`}>
                {speedLabel}
              </div>
              <div className="text-xs text-slate-500 mt-1 space-y-0.5">
                <div>P95: {fmt(thinkingSpeed, 0)}ms</div>
                <div>P50: {fmt(latest?.retrieve_p50_ms, 0)}ms</div>
              </div>
            </div>
            <div className="p-2 bg-cyan-500/10 rounded-xl">
              <Zap className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div className="mt-4 w-full bg-slate-800/50 rounded-full h-1.5 overflow-hidden">
            <div 
              className={`h-full rounded-full ${thinkingSpeed && thinkingSpeed < 100 ? "bg-emerald-500" : "bg-cyan-500"}`} 
              style={{ width: `${Math.min(100, Math.max(5, 100 - ((thinkingSpeed || 0) / 5)))}%` }} // Inverse: lower latency = higher bar
            />
          </div>
        </GlowCard>

        {/* Metric 2: Total Memories */}
        <GlowCard className="border-violet-400/20">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold mb-1">
                Total Memories
              </div>
              <div className="text-3xl font-bold text-violet-300">
                {fmtInt(latest?.nodes)}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Knowledge Nodes
              </div>
            </div>
            <div className="p-2 bg-violet-500/10 rounded-xl">
              <Database className="w-5 h-5 text-violet-400" />
            </div>
          </div>
          <div className="mt-4 text-xs text-violet-300/80">
            Growing steadily.
          </div>
        </GlowCard>

        {/* Metric 3: Health Status */}
        <GlowCard className="border-emerald-400/20">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold mb-1">
                System Status
              </div>
              <div className="text-3xl font-bold text-emerald-300">
                Online
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Efficiency: {efficiencyLabel}
              </div>
            </div>
            <div className="p-2 bg-emerald-500/10 rounded-xl">
              <Activity className="w-5 h-5 text-emerald-400" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs text-emerald-300/80">System systems operational</span>
          </div>
        </GlowCard>
      </div>

      {/* Evolution Health Panel - Surfaces FAIM Self-Evolution Concept */}
      {aggregate && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <GlowCard className="border-amber-400/10">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-xl">
                <Scissors className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold">Auto-Prune Events</div>
                <div className="text-2xl font-bold text-amber-300">{aggregate.prune_events}</div>
                <div className="text-xs text-slate-500">{fmt(aggregate.prune_rate_per_min, 2)}/min</div>
              </div>
            </div>
          </GlowCard>

          <GlowCard className="border-blue-400/10">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/10 rounded-xl">
                <TrendingUp className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold">Node Growth</div>
                <div className="text-2xl font-bold text-blue-300">{aggregate.node_growth >= 0 ? "+" : ""}{aggregate.node_growth}</div>
                <div className="text-xs text-slate-500">{fmt(aggregate.node_growth_per_min, 2)}/min</div>
              </div>
            </div>
          </GlowCard>

          <GlowCard className="border-purple-400/10">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/10 rounded-xl">
                <GitMerge className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold">Evolution Status</div>
                <div className="text-2xl font-bold text-purple-300">Active</div>
                <div className="text-xs text-slate-500">Self-optimizing</div>
              </div>
            </div>
          </GlowCard>
        </div>
      )}

      {/* Control Center */}
      <GlowCard className="p-0 overflow-hidden">
        <div className="p-5 border-b border-slate-800/50 flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-medium text-slate-50">Optimization Tools</h3>
            <p className="text-sm text-slate-400">Run diagnostics to check system health.</p>
          </div>
          <div className="flex items-center gap-2">
             <button
                type="button"
                onClick={() => runSchedule("Single snapshot", 0, undefined, 1)}
                disabled={!graphId || !!runStatus}
                className="flex items-center gap-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-4 py-2 text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {runStatus ? (
                  <><span className="animate-spin">⟳</span> Running...</>
                ) : (
                  <><Activity size={16} /> Run Health Check</>
                )}
              </button>
          </div>
        </div>
        
        {runStatus && (
           <div className="px-5 py-3 bg-cyan-500/5 border-b border-cyan-500/10 flex items-center justify-between">
             <span className="text-sm text-cyan-200">Diagnostics running: {runStatus}</span>
             <button onClick={stopRun} className="text-xs text-rose-400 hover:underline">Stop</button>
           </div>
        )}
      </GlowCard>

      {/* Advanced Details Toggle */}
      <div className="pt-4">
        <button 
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors mx-auto"
        >
          {showAdvanced ? "Hide Advanced Metrics" : "Show Advanced Metrics"}
          {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {showAdvanced && (
           <div className="mt-6 space-y-4 animate-in fade-in slide-in-from-top-4 duration-300">
             <div className="flex flex-wrap items-center justify-end gap-2">
                <Select
                  options={[
                    { value: "newest", label: "Newest" },
                    { value: "nodes", label: "Nodes" },
                    { value: "cr", label: "Efficiency" },
                    { value: "p95", label: "Latency" },
                  ]}
                  value={sortBy}
                  onChange={setSortBy}
                  size="sm"
                  className="w-[140px] border-cyan-500/10 bg-slate-950/40 text-cyan-50 hover:border-cyan-400/30 hover:bg-slate-900/60"
                />
                <Select
                   options={[
                    { value: "10", label: "10 rows" },
                    { value: "20", label: "20 rows" },
                    { value: "50", label: "50 rows" },
                    { value: "all", label: "All rows" },
                  ]}
                  value={limit}
                  onChange={setLimit}
                  size="sm"
                  className="w-[120px] border-cyan-500/10 bg-slate-950/40 text-cyan-50 hover:border-cyan-400/30 hover:bg-slate-900/60"
                />
             </div>

             <GlowCard className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-slate-400 bg-slate-950/30">
                    <tr className="border-b border-white/5">
                      <th className="py-3 pl-4 pr-3 font-medium">Timestamp</th>
                      <th className="py-3 pr-3 font-medium">Nodes</th>
                      <th className="py-3 pr-3 font-medium">Efficiency (CR)</th>
                      <th className="py-3 pr-3 font-medium">Drift</th>
                      <th className="py-3 pr-4 font-medium text-right">Latency (p95)</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-300">
                    {sortedFiltered.map((r) => (
                      <tr
                        key={r.id}
                        className="border-b border-white/5 hover:bg-white/5 transition-colors"
                      >
                        <td className="py-3 pl-4 pr-3 font-mono text-[11px] text-slate-400">
                          {r.timestamp ?? "—"}
                        </td>
                        <td className="py-3 pr-3">{fmtInt(r.nodes)}</td>
                        <td className="py-3 pr-3">{fmt(r.cr, 2)}x</td>
                        <td className="py-3 pr-3">{fmt(r.drift, 3)}</td>
                        <td className="py-3 pr-4 text-right">{fmt(r.retrieve_p95_ms, 1)} ms</td>
                      </tr>
                    ))}
                    {!sortedFiltered.length && (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-slate-500">
                          No data available. Run a health check to generate metrics.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </GlowCard>
           </div>
        )}
      </div>
    </div>
  );
}

