"use client";

import React, { useEffect, useState } from "react";
import { Database, Server, Boxes } from "lucide-react";

interface ResourceStats {
  redis: {
    status: string;
    memory_mb: number;
    connected_clients: number;
    memory_peak_mb?: number;
  };
  postgres: {
    status: string;
    connections: number;
    database_size_mb: number;
  };
  qdrant: {
    status: string;
    collections: number;
    vectors_count: number;
    storage_mb: number;
  };
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "healthy"
      ? "bg-emerald-400"
      : status === "offline"
      ? "bg-slate-500"
      : "bg-rose-400";
  return (
    <span
      className={`h-2 w-2 rounded-full ${color} shadow-[0_0_6px_currentColor]`}
    />
  );
}

function formatMB(mb: number): string {
  if (mb < 1) return `${Math.round(mb * 1024)} KB`;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}

export function ResourceUsagePanel() {
  const [stats, setStats] = useState<ResourceStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/ops/resources")
      .then((r) => r.json())
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="grid gap-3 md:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-slate-800/50 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (!stats || !stats.redis || !stats.postgres || !stats.qdrant) {
    return (
      <div className="text-center py-6 text-[11px] text-slate-500">
        Unable to load resource stats
      </div>
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {/* Redis */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Server size={16} className="text-rose-400" />
            <span className="text-xs font-semibold text-slate-100">Redis</span>
          </div>
          <StatusDot status={stats.redis.status} />
        </div>
        <div className="space-y-2 text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-500">Memory</span>
            <span className="text-slate-200">{formatMB(stats.redis.memory_mb)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Clients</span>
            <span className="text-slate-200">{stats.redis.connected_clients}</span>
          </div>
          {stats.redis.memory_peak_mb && (
            <div className="flex justify-between">
              <span className="text-slate-500">Peak</span>
              <span className="text-slate-200">{formatMB(stats.redis.memory_peak_mb)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Postgres */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Database size={16} className="text-cyan-400" />
            <span className="text-xs font-semibold text-slate-100">Postgres</span>
          </div>
          <StatusDot status={stats.postgres.status} />
        </div>
        <div className="space-y-2 text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-500">Connections</span>
            <span className="text-slate-200">{stats.postgres.connections}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">DB Size</span>
            <span className="text-slate-200">{formatMB(stats.postgres.database_size_mb)}</span>
          </div>
        </div>
      </div>

      {/* Qdrant */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Boxes size={16} className="text-violet-400" />
            <span className="text-xs font-semibold text-slate-100">Qdrant</span>
          </div>
          <StatusDot status={stats.qdrant.status} />
        </div>
        <div className="space-y-2 text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-500">Collections</span>
            <span className="text-slate-200">{stats.qdrant.collections}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Vectors</span>
            <span className="text-slate-200">{stats.qdrant.vectors_count.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Storage</span>
            <span className="text-slate-200">{formatMB(stats.qdrant.storage_mb)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
