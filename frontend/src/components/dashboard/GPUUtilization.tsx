"use client";

import React, { useMemo } from "react";

interface GPUUtilizationProps {
  gpuAvailable: boolean;
  gpuActive: boolean;
  throughput: number;
}

export const GPUUtilization: React.FC<GPUUtilizationProps> = ({
  gpuAvailable,
  gpuActive,
  throughput,
}) => {
  const utilization = useMemo(() => {
    if (!gpuAvailable) return { level: 0, label: "Unavailable", color: "#64748b" };
    if (!gpuActive) return { level: 0, label: "Idle (CPU)", color: "#64748b" };
    // Estimate utilization from throughput (jobs/s) — rough heuristic
    const level = Math.min(1, Math.max(0, throughput / 5)); // 5 jobs/s = 100%
    if (level >= 0.7) return { level, label: "High", color: "#f87171" };
    if (level >= 0.3) return { level, label: "Moderate", color: "#fbbf24" };
    return { level, label: "Low", color: "#34d399" };
  }, [gpuAvailable, gpuActive, throughput]);

  if (!gpuAvailable) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 h-full w-full">
        <div className="relative w-32 h-32">
          <svg width="128" height="128" viewBox="0 0 128 128">
            <circle
              cx="64"
              cy="64"
              r="56"
              fill="none"
              stroke="#1e293b"
              strokeWidth="10"
            />
            <circle
              cx="64"
              cy="64"
              r="56"
              fill="none"
              stroke="#64748b"
              strokeWidth="10"
              strokeDasharray="351.86"
              strokeDashoffset="351.86"
              transform="rotate(-90 64 64)"
            />
          </svg>
        </div>
        <div className="text-center">
          <p className="text-[20px] font-mono font-bold text-slate-500">GPU N/A</p>
          <p className="text-[9px] uppercase tracking-wider text-slate-600">Acceleration disabled</p>
        </div>
      </div>
    );
  }

  const circumference = 2 * Math.PI * 56;
  const strokeDashoffset = circumference * (1 - utilization.level);

  return (
    <div className="flex flex-col items-center justify-center gap-3 h-full w-full">
      <div className="relative w-32 h-32">
        <svg width="128" height="128" viewBox="0 0 128 128">
          <circle
            cx="64"
            cy="64"
            r="56"
            fill="none"
            stroke="#1e293b"
            strokeWidth="10"
          />
          <circle
            cx="64"
            cy="64"
            r="56"
            fill="none"
            stroke={utilization.color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform="rotate(-90 64 64)"
            style={{ transition: "stroke-dashoffset 0.6s ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[22px] font-mono font-bold text-white">
            {(utilization.level * 100).toFixed(0)}%
          </span>
          <span className="text-[8px] font-mono uppercase tracking-wider text-slate-500">
            Utilization
          </span>
        </div>
      </div>
      <div className="text-center">
        <p className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
          GPU {utilization.label}
        </p>
        <p className="text-[9px] text-slate-600">
          {throughput.toFixed(2)} jobs/s throughput
        </p>
      </div>
    </div>
  );
};