"use client";

import React, { useMemo } from "react";

interface CacheHitRateRingProps {
  hitRate: number | null;
  totalRequests: number;
  label?: string;
}

export const CacheHitRateRing: React.FC<CacheHitRateRingProps> = ({
  hitRate,
  totalRequests,
  label = "Cache Hit Rate",
}) => {
  const progress = useMemo(() => {
    if (hitRate === null || totalRequests === 0) return 0;
    return Math.max(0, Math.min(1, hitRate));
  }, [hitRate, totalRequests]);

  const circumference = 2 * Math.PI * 52;
  const strokeDashoffset = circumference * (1 - progress);

  const color =
    progress >= 0.8
      ? "#34d399"
      : progress >= 0.5
        ? "#fbbf24"
        : progress > 0
          ? "#f87171"
          : "#64748b";

  if (hitRate === null) {
    return (
      <div className="flex-1 min-h-[140px] w-full flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/10 bg-white/[0.01] text-slate-500">
        <span className="text-[11px] font-mono">No cache telemetry yet</span>
        <p className="text-[9px] text-slate-600">Hit rate appears after first queries</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3 h-full w-full">
      <svg width="130" height="130" viewBox="0 0 130 130">
        <circle
          cx="65"
          cy="65"
          r="52"
          fill="none"
          stroke="#1e293b"
          strokeWidth="8"
        />
        <circle
          cx="65"
          cy="65"
          r="52"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform="rotate(-90 65 65)"
          style={{ transition: "stroke-dashoffset 0.6s ease-out" }}
        />
      </svg>
      <div className="text-center">
        <div className="text-[28px] font-mono font-bold text-white" style={{ color }}>
          {(progress * 100).toFixed(1)}%
        </div>
        <div className="text-[9px] font-mono uppercase tracking-wider text-slate-500 mt-1">
          {label}
        </div>
        <div className="text-[8px] text-slate-600 mt-0.5">
          {totalRequests.toLocaleString()} requests
        </div>
      </div>
    </div>
  );
};