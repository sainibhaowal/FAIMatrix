"use client";

import React, { useEffect, useState } from "react";
import { Zap, Cpu, Activity, BarChart3 } from "lucide-react";
import { getSession } from "next-auth/react";

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

export function NeuralCoreStatus() {
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const session = await getSession();
        const token = (session as any)?.accessToken;
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/v1/pipeline/stats", { headers });
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (e) {
        console.error("Failed to fetch pipeline stats", e);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) return null;

  return (
    <div className="flex items-center gap-4 px-3 py-1.5 rounded-xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-md">
      {/* GPU Badge */}
      <div className="flex items-center gap-1.5">
        <div
          className={`p-1 rounded-md ${stats?.gpu_active ? "bg-amber-500/10" : "bg-slate-800"}`}
        >
          <Zap
            size={12}
            className={
              stats?.gpu_active
                ? "text-amber-400 animate-pulse"
                : "text-slate-500"
            }
          />
        </div>
        <div className="flex flex-col">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">
            Engine
          </span>
          <span
            className={`text-[10px] font-semibold ${stats?.gpu_active ? "text-amber-400" : "text-slate-300"}`}
          >
            {stats?.gpu_active ? "GPU ACCEL" : "CPU OPTIMIZED"}
          </span>
        </div>
      </div>

      <div className="h-6 w-px bg-slate-800" />

      {/* Queue Status */}
      <div className="flex items-center gap-1.5">
        <div
          className={`p-1 rounded-md ${stats?.queue_depth && stats.queue_depth > 0 ? "bg-cyan-500/10" : "bg-slate-800"}`}
        >
          <Activity
            size={12}
            className={
              stats?.queue_depth && stats.queue_depth > 0
                ? "text-cyan-400 animate-pulse"
                : "text-slate-500"
            }
          />
        </div>
        <div className="flex flex-col">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">
            Throughput
          </span>
          <span className="text-[10px] font-semibold text-cyan-400">
            {stats?.throughput.toFixed(1)}{" "}
            <span className="text-slate-500 font-normal">nodes/s</span>
          </span>
        </div>
      </div>

      <div className="h-6 w-px bg-slate-800" />

      {/* Cache Status */}
      <div className="flex items-center gap-1.5">
        <div className="p-1 rounded-md bg-violet-500/10 text-violet-400">
          <BarChart3 size={12} />
        </div>
        <div className="flex flex-col">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">
            Hot Cache
          </span>
          <span className="text-[10px] font-semibold text-violet-400">
            {stats?.hot_cache_size}{" "}
            <span className="text-slate-500 font-normal">items</span>
          </span>
        </div>
      </div>

      <div className="h-6 w-px bg-slate-800" />

      {/* System Health */}
      <div className="flex items-center gap-3">
        <div className="flex flex-col pr-1">
          <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">
            Stack
          </span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <div
              title="Redis Cache"
              className={`w-1.5 h-1.5 rounded-full ${stats?.system_health?.redis ? "bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]" : "bg-red-500"}`}
            />
            <div
              title="Qdrant Vector DB"
              className={`w-1.5 h-1.5 rounded-full ${stats?.system_health?.qdrant ? "bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]" : "bg-red-500"}`}
            />
            <div
              title="AES encryption"
              className={`w-1.5 h-1.5 rounded-full ${stats?.system_health?.encryption ? "bg-blue-500 shadow-[0_0_5px_rgba(59,130,246,0.5)]" : "bg-slate-700"}`}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
