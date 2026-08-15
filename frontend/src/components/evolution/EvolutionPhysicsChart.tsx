"use client";

import React, { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface EvolutionPhysicsPoint {
  time: string;
  seq?: number;
  entropy: number;      // H
  redundancy: number;   // R
  novelty: number;      // N
  pressure: number;     // Lambda
  energy: number;       // E
}

interface EvolutionPhysicsChartProps {
  data: EvolutionPhysicsPoint[];
}

export const EvolutionPhysicsChart: React.FC<EvolutionPhysicsChartProps> = ({ data }) => {
  const [activeSeries, setActiveSeries] = useState<{
    redundancy: boolean;
    novelty: boolean;
    pressure: boolean;
    entropy: boolean;
    energy: boolean;
  }>({
    redundancy: true,
    novelty: true,
    pressure: true,
    entropy: true,
    energy: false,
  });

  const chartData =
    data.length > 0
      ? data
      : [
          { time: "T-5", entropy: 0.18, redundancy: 0.05, novelty: 0.95, pressure: 0.1, energy: 0.8 },
          { time: "T-4", entropy: 0.32, redundancy: 0.12, novelty: 0.88, pressure: 0.22, energy: 0.95 },
          { time: "T-3", entropy: 0.48, redundancy: 0.28, novelty: 0.72, pressure: 0.41, energy: 1.15 },
          { time: "T-2", entropy: 0.65, redundancy: 0.45, novelty: 0.55, pressure: 0.58, energy: 1.42 },
          { time: "T-1", entropy: 0.52, redundancy: 0.22, novelty: 0.78, pressure: 0.31, energy: 1.08 },
          { time: "Now", entropy: 0.41, redundancy: 0.14, novelty: 0.86, pressure: 0.19, energy: 0.92 },
        ];

  return (
    <div className="flex flex-col h-full w-full">
      {/* Series Toggle Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 px-1">
        <div className="flex flex-wrap items-center space-x-2">
          <button
            type="button"
            onClick={() =>
              setActiveSeries((s) => ({ ...s, redundancy: !s.redundancy }))
            }
            className={`px-2 py-0.5 rounded text-[10px] font-mono tracking-wider transition-colors border ${
              activeSeries.redundancy
                ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                : "bg-slate-800/40 text-slate-500 border-slate-700/30"
            }`}
          >
            ● Redundancy (R)
          </button>
          <button
            type="button"
            onClick={() =>
              setActiveSeries((s) => ({ ...s, novelty: !s.novelty }))
            }
            className={`px-2 py-0.5 rounded text-[10px] font-mono tracking-wider transition-colors border ${
              activeSeries.novelty
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                : "bg-slate-800/40 text-slate-500 border-slate-700/30"
            }`}
          >
            ● Novelty (N)
          </button>
          <button
            type="button"
            onClick={() =>
              setActiveSeries((s) => ({ ...s, pressure: !s.pressure }))
            }
            className={`px-2 py-0.5 rounded text-[10px] font-mono tracking-wider transition-colors border ${
              activeSeries.pressure
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : "bg-slate-800/40 text-slate-500 border-slate-700/30"
            }`}
          >
            ● Pressure (λ)
          </button>
          <button
            type="button"
            onClick={() =>
              setActiveSeries((s) => ({ ...s, entropy: !s.entropy }))
            }
            className={`px-2 py-0.5 rounded text-[10px] font-mono tracking-wider transition-colors border ${
              activeSeries.entropy
                ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                : "bg-slate-800/40 text-slate-500 border-slate-700/30"
            }`}
          >
            ● Entropy (H)
          </button>
          <button
            type="button"
            onClick={() =>
              setActiveSeries((s) => ({ ...s, energy: !s.energy }))
            }
            className={`px-2 py-0.5 rounded text-[10px] font-mono tracking-wider transition-colors border ${
              activeSeries.energy
                ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                : "bg-slate-800/40 text-slate-500 border-slate-700/30"
            }`}
          >
            ● Energy (E)
          </button>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">
          Graph Invariants Stream
        </span>
      </div>

      {/* Recharts Canvas */}
      <div className="h-[280px] w-full relative">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
          >
            <defs>
              <linearGradient id="gradientRedundancy" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="gradientNovelty" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="gradientPressure" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="gradientEntropy" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="gradientEnergy" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#a855f7" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#a855f7" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.05)"
              vertical={false}
            />
            <XAxis
              dataKey="time"
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <YAxis
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              domain={[0, "auto"]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(11, 18, 32, 0.95)",
                borderColor: "rgba(255, 255, 255, 0.15)",
                borderRadius: "12px",
                fontSize: "12px",
                backdropFilter: "blur(12px)",
                color: "#f8fafc",
                boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
              }}
            />
            {activeSeries.redundancy && (
              <Area
                type="monotone"
                dataKey="redundancy"
                name="Redundancy (R)"
                stroke="#f43f5e"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradientRedundancy)"
              />
            )}
            {activeSeries.novelty && (
              <Area
                type="monotone"
                dataKey="novelty"
                name="Novelty (N)"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradientNovelty)"
              />
            )}
            {activeSeries.pressure && (
              <Area
                type="monotone"
                dataKey="pressure"
                name="Pressure (λ)"
                stroke="#f59e0b"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradientPressure)"
              />
            )}
            {activeSeries.entropy && (
              <Area
                type="monotone"
                dataKey="entropy"
                name="Entropy (H)"
                stroke="#06b6d4"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradientEntropy)"
              />
            )}
            {activeSeries.energy && (
              <Area
                type="monotone"
                dataKey="energy"
                name="Energy (E)"
                stroke="#a855f7"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradientEnergy)"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
