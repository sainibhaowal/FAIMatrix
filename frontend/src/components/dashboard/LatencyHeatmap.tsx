"use client";

import React from "react";

interface PipelineStats {
  gpu_available: boolean;
  gpu_active: boolean;
  throughput: number;
  hot_cache_size: number;
  queue_depth: number;
  system_health: {
    redis: boolean;
    qdrant: boolean;
    encryption: boolean;
  };
}

interface LatencyHeatmapProps {
  data: PipelineStats | null;
}

const TIERS = [
  { key: "queue_depth", label: "Queue Depth", unit: "", warn: 50, crit: 100 },
  { key: "throughput", label: "Throughput (jobs/s)", unit: "/s", warn: 0.5, crit: 0.1 },
  { key: "hot_cache_size", label: "Hot Cache", unit: " keys", warn: 100, crit: 1000 },
] as const;

export const LatencyHeatmap: React.FC<LatencyHeatmapProps> = ({ data }) => {
  if (!data) {
    return (
      <div className="flex-1 min-h-[140px] w-full flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/10 bg-white/[0.01] text-slate-500">
        <span className="text-[11px] font-mono">Loading pipeline telemetry…</span>
        <p className="text-[9px] text-slate-600">Queue depth, throughput, cache size</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full gap-2">
      <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-slate-500">
        <span>Pipeline Health</span>
        <span className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${data.system_health.redis ? "bg-emerald-400" : "bg-rose-400"}`} />
          <span className="text-cyan-400">Redis</span>
          <span className={`w-2 h-2 rounded-full ${data.system_health.qdrant ? "bg-emerald-400" : "bg-rose-400"}`} />
          <span className="text-blue-400">Qdrant</span>
          <span className={`w-2 h-2 rounded-full ${data.gpu_active ? "bg-emerald-400" : "bg-slate-500"}`} />
          <span className="text-violet-400">GPU</span>
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 flex-1">
        {TIERS.map((t) => {
          const val = data[t.key as keyof PipelineStats] as number;
          const isWarn = t.key === "throughput" ? val < t.warn : val > t.warn;
          const isCrit = t.key === "throughput" ? val < t.crit : val > t.crit;
          return (
            <div
              key={t.key}
              className={`relative rounded-[12px] border p-3 flex flex-col items-center justify-center gap-1 transition-colors ${
                isCrit
                  ? "border-rose-400/40 bg-rose-400/10"
                  : isWarn
                    ? "border-amber-400/40 bg-amber-400/10"
                    : "border-emerald-400/30 bg-emerald-400/10"
              }`}
            >
              <div className="text-[14px] font-mono font-bold text-white">
                {t.key === "throughput" ? val.toFixed(2) : val.toLocaleString()}
              </div>
              <div className="text-[8px] font-mono uppercase tracking-wider text-slate-500">
                {t.label}
              </div>
              <div className="absolute bottom-1 right-1 w-2 h-2 rounded-full transition-colors" style={{
                background: isCrit ? "#f87171" : isWarn ? "#fbbf24" : "#34d399",
              }} />
            </div>
          );
        })}
      </div>
    </div>
  );
};