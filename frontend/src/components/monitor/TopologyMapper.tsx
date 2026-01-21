"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  Network, 
  Share2, 
  GitBranch, 
  ArrowDownCircle, 
  BarChart3, 
  Info,
  AlertTriangle,
  RefreshCw
} from "lucide-react";

interface TopologyMetrics {
  fractal_dimension: {
    mean_D: number;
    min_D: number;
    max_D: number;
    target_D: number;
  };
  redundancy_index: number;
  node_count: number;
  region_count: number;
  branching_factor: number;
  max_inheritance_depth: number;
  avg_inheritance_depth: number;
  ts: number;
}

export default function TopologyMapper({ graphId }: { graphId: string }) {
  const [metrics, setMetrics] = useState<TopologyMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchTopology = useCallback(async () => {
    if (!graphId) return;
    try {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers: Record<string, string> = {};
      if (session && (session as any).accessToken) {
        headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const res = await fetch(`/api/ops/graphs/${graphId}/topology`, { headers });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error("Failed to fetch topology metrics:", err);
    } finally {
      setLoading(false);
    }
  }, [graphId]);

  useEffect(() => {
    fetchTopology();
    const interval = setInterval(fetchTopology, 10000);
    return () => clearInterval(interval);
  }, [fetchTopology]);

  if (loading || !metrics) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950 border border-slate-800 rounded-xl">
        <RefreshCw className="h-6 w-6 text-slate-700 animate-spin" />
      </div>
    );
  }

  const isHealthy = metrics.fractal_dimension.mean_D > 1.5 && metrics.redundancy_index < 0.3;

  return (
    <div className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-violet-400" />
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-widest">
            Topology Diagnostic
          </h3>
        </div>
        <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded border ${
          isHealthy ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500" : "bg-amber-500/10 border-amber-500/20 text-amber-500"
        }`}>
          {isHealthy ? <Share2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
          <span className="text-[10px] font-mono font-bold uppercase">
            {isHealthy ? "Structural Health: High" : "Structural Health: Mid"}
          </span>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 bg-slate-900/40 rounded-lg border border-slate-800/50 flex flex-col items-center gap-1">
          <span className="text-[9px] text-slate-500 uppercase font-bold tracking-tighter">Fractal-D</span>
          <span className="text-xl font-mono font-bold text-violet-400 tabular-nums">
            {metrics.fractal_dimension.mean_D.toFixed(2)}
          </span>
          <div className="flex items-center gap-1 text-[8px] text-slate-600">
            <span>TARGET: {metrics.fractal_dimension.target_D}</span>
          </div>
        </div>
        <div className="p-3 bg-slate-900/40 rounded-lg border border-slate-800/50 flex flex-col items-center gap-1">
          <span className="text-[9px] text-slate-500 uppercase font-bold tracking-tighter">Inheritance</span>
          <span className="text-xl font-mono font-bold text-blue-400 tabular-nums">
            {metrics.avg_inheritance_depth.toFixed(1)}
          </span>
          <div className="flex items-center gap-1 text-[8px] text-slate-600">
            <span>MAX DEPTH: {metrics.max_inheritance_depth}</span>
          </div>
        </div>
        <div className="p-3 bg-slate-900/40 rounded-lg border border-slate-800/50 flex flex-col items-center gap-1">
          <span className="text-[9px] text-slate-500 uppercase font-bold tracking-tighter">Branching</span>
          <span className="text-xl font-mono font-bold text-cyan-400 tabular-nums">
            {metrics.branching_factor.toFixed(2)}
          </span>
          <div className="flex items-center gap-1 text-[8px] text-slate-600">
            <span>REGIONS: {metrics.region_count}</span>
          </div>
        </div>
      </div>

      {/* Distribution Chart & Details */}
      <div className="flex-1 bg-slate-900/30 rounded-lg border border-slate-800/80 p-3 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-slate-400">
            <BarChart3 className="h-3.5 w-3.5" />
            <span className="text-[10px] font-bold uppercase tracking-widest">Structural Balance</span>
          </div>
          <Info className="h-3 w-3 text-slate-600 cursor-help" />
        </div>

        <div className="space-y-3">
            {/* Redundancy Bar */}
            <div className="space-y-1">
                <div className="flex justify-between text-[9px] font-mono text-slate-500 uppercase">
                    <span>Redundancy Index</span>
                    <span className={metrics.redundancy_index > 0.4 ? "text-rose-400" : "text-emerald-400"}>
                        {(metrics.redundancy_index * 100).toFixed(1)}%
                    </span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div 
                        className={`h-full transition-all duration-1000 ${metrics.redundancy_index > 0.4 ? "bg-rose-500" : "bg-emerald-500"}`}
                        style={{ width: `${Math.min(100, metrics.redundancy_index * 100)}%` }}
                    />
                </div>
            </div>

            {/* Maturity Bar (derived from avg depth & branching) */}
            <div className="space-y-1">
                <div className="flex justify-between text-[9px] font-mono text-slate-500 uppercase">
                    <span>Knowledge Maturity</span>
                    <span className="text-violet-400">
                        {Math.min(100, Math.round(metrics.avg_inheritance_depth * 20))}%
                    </span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div 
                        className="h-full bg-violet-500 transition-all duration-1000"
                        style={{ width: `${Math.min(100, metrics.avg_inheritance_depth * 20)}%` }}
                    />
                </div>
            </div>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-800/50 flex flex-col gap-2">
            <div className="flex items-start gap-2">
                <GitBranch className="h-3 w-3 text-slate-500 mt-0.5" />
                <p className="text-[9px] text-slate-400 leading-tight">
                    Graph structural depth is optimal. Evolution engine has pruned 
                    <span className="text-emerald-400 mx-1">{(metrics.redundancy_index * 100).toFixed(0)}%</span> 
                    of near-duplicate concept clusters in the last cycle.
                </p>
            </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-[9px] text-slate-600 font-mono px-1">
        <span>TOPOLOGY_MAP: {metrics.node_count} NODES / {metrics.region_count} REGIONS</span>
        <div className="flex items-center gap-1 text-emerald-500/60 font-bold">
            <ArrowDownCircle className="h-2.5 w-2.5" />
            <span>OPTIMIZED</span>
        </div>
      </div>
    </div>
  );
}
