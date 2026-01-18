"use client";

import React, { useState, useEffect } from "react";
import { 
  Zap, 
  Cpu, 
  Database, 
  Layers, 
  HardDrive, 
  ArrowUpRight,
  ShieldCheck,
  Activity
} from "lucide-react";

interface EngineMetrics {
  hot_cache: {
    hits: number;
    misses: number;
    puts: number;
    evictions: number;
    size: number;
    hit_rate: number;
  };
  vector_bank: {
    total_graphs: number;
    graph_sizes: Record<string, number>;
    max_graphs: number;
    allow_gpu: boolean;
  };
  write_queue: {
    queued: number;
    last_commit_seq: number;
    max_size: number;
    latency_ms: number;
  };
  nodes_per_sec: number;
  ts: number;
}

export default function EnginePerformance() {
  const [metrics, setMetrics] = useState<EngineMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = async () => {
    try {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers: Record<string, string> = {};
      if (session && (session as any).accessToken) {
        headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const res = await fetch("/api/ops/engine/metrics", { headers });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error("Failed to fetch engine metrics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 3000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !metrics) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950 border border-slate-800 rounded-xl">
        <Activity className="h-6 w-6 text-slate-700 animate-pulse" />
      </div>
    );
  }

  const cacheHitRate = Math.round(metrics.hot_cache.hit_rate * 100);
  const queuePressure = Math.round((metrics.write_queue.queued / (metrics.write_queue.max_size || 100000)) * 100);
  const vbUtilization = Math.round((metrics.vector_bank.total_graphs / metrics.vector_bank.max_graphs) * 100);

  return (
    <div className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-400" />
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-widest">
            HyperSpeed Performance
          </h3>
        </div>
        <div className="flex items-center gap-2 px-2 py-0.5 bg-amber-500/10 rounded border border-amber-500/20">
          <Cpu className="h-3 w-3 text-amber-500" />
          <span className="text-[10px] font-mono text-amber-500 font-bold">P4.ENGINE</span>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 gap-4 flex-1">
        {/* HotNodeCache (Tier-2) */}
        <div className="flex flex-col gap-3 p-3 bg-slate-900/50 rounded-lg border border-slate-800/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Layers className="h-3.5 w-3.5" />
              <span className="text-[10px] font-bold uppercase tracking-tighter">HotNode Cache</span>
            </div>
            <span className="text-[10px] tabular-nums text-slate-500">{metrics.hot_cache.size} Nodes</span>
          </div>
          
          <div className="space-y-1">
            <div className="flex justify-between text-[9px] text-slate-500 uppercase font-mono">
              <span>Hit Rate</span>
              <span className={cacheHitRate > 70 ? "text-emerald-400" : "text-amber-400"}>{cacheHitRate}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-1000 ${cacheHitRate > 70 ? "bg-emerald-500" : "bg-amber-500"}`}
                style={{ width: `${cacheHitRate}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 mt-auto">
            <div className="text-center p-1.5 bg-slate-950 rounded border border-slate-800/50">
              <div className="text-[16px] font-bold text-slate-200 tabular-nums">{metrics.hot_cache.hits}</div>
              <div className="text-[8px] text-slate-600 uppercase">Hits</div>
            </div>
            <div className="text-center p-1.5 bg-slate-950 rounded border border-slate-800/50">
              <div className="text-[16px] font-bold text-slate-500 tabular-nums">{metrics.hot_cache.misses}</div>
              <div className="text-[8px] text-slate-600 uppercase">Misses</div>
            </div>
          </div>
        </div>

        {/* Write Queue (Durability) */}
        <div className="flex flex-col gap-3 p-3 bg-slate-900/50 rounded-lg border border-slate-800/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-slate-400">
              <HardDrive className="h-3.5 w-3.5" />
              <span className="text-[10px] font-bold uppercase tracking-tighter">Write Queue</span>
            </div>
            <span className="text-[10px] tabular-nums text-slate-500">{metrics.write_queue.queued} Enqueued</span>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[9px] text-slate-500 uppercase font-mono">
              <span>Pressure</span>
              <span className={queuePressure > 50 ? "text-rose-400" : "text-blue-400"}>{queuePressure}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-1000 ${queuePressure > 50 ? "bg-rose-500" : "bg-blue-500"}`}
                style={{ width: `${Math.max(2, queuePressure)}%` }}
              />
            </div>
          </div>

          <div className="mt-auto grid grid-cols-2 gap-2">
            <div className="text-center p-1.5 bg-slate-950 rounded border border-slate-800/50">
              <div className="text-[14px] font-bold text-slate-200 tabular-nums">{metrics.write_queue.latency_ms}ms</div>
              <div className="text-[8px] text-slate-600 uppercase">Wait</div>
            </div>
            <div className="text-center p-1.5 bg-slate-950 rounded border border-slate-800/50">
               <div className="text-[14px] font-bold text-slate-200 tabular-nums">{metrics.write_queue.last_commit_seq}</div>
               <div className="text-[8px] text-slate-600 uppercase">Seq</div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Stats */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-900/30 rounded-lg border border-slate-800">
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <span className="text-[8px] text-slate-600 uppercase font-bold">VectorBank</span>
            <div className="flex items-center gap-1.5">
              <Database className="h-3 w-3 text-violet-500" />
              <span className="text-[11px] font-mono text-slate-300 tabular-nums">
                {metrics.vector_bank.total_graphs}/{metrics.vector_bank.max_graphs}
              </span>
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-[8px] text-slate-600 uppercase font-bold">GPU Backend</span>
            <span className={`text-[11px] font-mono ${metrics.vector_bank.allow_gpu ? "text-emerald-500" : "text-rose-500"}`}>
              {metrics.vector_bank.allow_gpu ? "ENABLED" : "DISABLED"}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end">
           <span className="text-[8px] text-slate-600 uppercase font-bold">Throughput</span>
           <div className="flex items-center gap-1 text-emerald-400">
             <span className="text-[14px] font-bold tabular-nums">{metrics.nodes_per_sec.toFixed(2)}</span>
             <span className="text-[9px] uppercase">Nodes/s</span>
             <ArrowUpRight className="h-2 w-2" />
           </div>
        </div>
      </div>
    </div>
  );
}
