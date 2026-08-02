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

export interface GraphHealthPoint {
  time: string;
  entropy: number;
  density: number;
  spectral_radius: number;
}

interface GraphHealthChartProps {
  data: GraphHealthPoint[];
}

export const GraphHealthChart: React.FC<GraphHealthChartProps> = ({ data }) => {
  const [activeSeries, setActiveSeries] = useState<{
    entropy: boolean;
    density: boolean;
    spectral: boolean;
  }>({
    entropy: true,
    density: true,
    spectral: true,
  });

  const chartData = data.length > 0 ? data : [
    { time: "00:00", entropy: 0, density: 0, spectral_radius: 0 },
    { time: "04:00", entropy: 0.12, density: 0.05, spectral_radius: 0.2 },
    { time: "08:00", entropy: 0.35, density: 0.18, spectral_radius: 0.45 },
    { time: "12:00", entropy: 0.58, density: 0.32, spectral_radius: 0.68 },
    { time: "16:00", entropy: 0.72, density: 0.41, spectral_radius: 0.81 },
    { time: "20:00", entropy: 0.85, density: 0.49, spectral_radius: 0.92 },
  ];

  return (
    <div className="flex flex-col h-full w-full">
      {/* Series Toggle Controls */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center space-x-2">
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
              setActiveSeries((s) => ({ ...s, density: !s.density }))
            }
            className={`px-2 py-0.5 rounded text-[10px] font-mono tracking-wider transition-colors border ${
              activeSeries.density
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                : "bg-slate-800/40 text-slate-500 border-slate-700/30"
            }`}
          >
            ● Density (D)
          </button>
          <button
            type="button"
            onClick={() =>
              setActiveSeries((s) => ({ ...s, spectral: !s.spectral }))
            }
            className={`px-2 py-0.5 rounded text-[10px] font-mono tracking-wider transition-colors border ${
              activeSeries.spectral
                ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                : "bg-slate-800/40 text-slate-700/30"
            }`}
          >
            ● Spectral (Λ)
          </button>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">Realtime Scorecard</span>
      </div>

      {/* Recharts Canvas */}
      <div className="h-[300px] w-full relative">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
          >
            <defs>
              <linearGradient id="gradientEntropy" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="gradientDensity" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="gradientSpectral" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#a855f7" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#a855f7" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
            <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={[0, 1]} />

            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-slate-900/95 border border-cyan-500/40 p-2.5 rounded-lg shadow-xl backdrop-blur-md text-[11px] font-mono">
                      <p className="text-slate-400 font-bold mb-1.5">{label}</p>
                      {payload.map((entry, idx) => (
                        <div
                          key={`item-${idx}`}
                          className="flex items-center justify-between space-x-3 py-0.5"
                          style={{ color: entry.color }}
                        >
                          <span>{entry.name}:</span>
                          <span className="font-bold tabular-nums">
                            {Number(entry.value).toFixed(4)}
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                }
                return null;
              }}
            />

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

            {activeSeries.density && (
              <Area
                type="monotone"
                dataKey="density"
                name="Density (D)"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradientDensity)"
              />
            )}

            {activeSeries.spectral && (
              <Area
                type="monotone"
                dataKey="spectral_radius"
                name="Spectral (Λ)"
                stroke="#a855f7"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#gradientSpectral)"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
