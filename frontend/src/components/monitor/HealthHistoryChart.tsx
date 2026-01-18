"use client";

import React, { useEffect, useState } from "react";
import { Activity } from "lucide-react";

interface HealthPoint {
  timestamp: string;
  db_ok: boolean;
  redis_ok: boolean;
  latency_ms: number;
}

export function HealthHistoryChart() {
  const [history, setHistory] = useState<HealthPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/ops/health-history")
      .then((r) => r.json())
      .then((data) => {
        setHistory(Array.isArray(data) ? data.slice(0, 48) : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="h-32 bg-slate-800/50 rounded-xl animate-pulse" />
    );
  }

  if (history.length === 0) {
    return (
      <div className="text-center py-8 text-[11px] text-slate-500">
        No health history available
      </div>
    );
  }

  // Calculate chart dimensions
  const chartWidth = 100;
  const chartHeight = 60;
  const padding = 4;
  const maxLatency = Math.max(...history.map((h) => h.latency_ms), 50);
  const minLatency = Math.min(...history.map((h) => h.latency_ms), 0);
  const latencyRange = maxLatency - minLatency || 1;

  // Build SVG path for latency line
  const points = history.map((h, i) => {
    const x = padding + ((chartWidth - 2 * padding) * i) / (history.length - 1 || 1);
    const y = chartHeight - padding - ((h.latency_ms - minLatency) / latencyRange) * (chartHeight - 2 * padding);
    return { x, y, ok: h.db_ok && h.redis_ok, latency: h.latency_ms };
  });

  const linePath = points.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(" ");

  // Gradient area
  const areaPath = `${linePath} L ${points[points.length - 1]?.x || 0} ${chartHeight - padding} L ${padding} ${chartHeight - padding} Z`;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
          <Activity size={14} className="text-cyan-400" />
          Health History (24h)
        </h3>
        <div className="flex items-center gap-3 text-[10px] text-slate-500">
          <span>Avg: {Math.round(history.reduce((a, h) => a + h.latency_ms, 0) / history.length)}ms</span>
          <span>Max: {maxLatency}ms</span>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full h-20"
          preserveAspectRatio="none"
        >
          {/* Gradient fill */}
          <defs>
            <linearGradient id="healthGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="rgba(34, 211, 238, 0.3)" />
              <stop offset="100%" stopColor="rgba(34, 211, 238, 0)" />
            </linearGradient>
          </defs>

          {/* Area fill */}
          <path d={areaPath} fill="url(#healthGradient)" />

          {/* Line */}
          <path
            d={linePath}
            fill="none"
            stroke="rgba(34, 211, 238, 0.8)"
            strokeWidth="0.5"
            vectorEffect="non-scaling-stroke"
          />

          {/* Status dots */}
          {points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r="1"
              fill={p.ok ? "#22d3ee" : "#f87171"}
            />
          ))}
        </svg>

        {/* Legend */}
        <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500">
          <span>24h ago</span>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
              Healthy
            </span>
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
              Unhealthy
            </span>
          </div>
          <span>Now</span>
        </div>
      </div>
    </div>
  );
}
