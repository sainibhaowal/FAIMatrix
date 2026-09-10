"use client";

import React from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface TelemetryPoint {
  seq: number;
  time: string;
  velocity: number;
}

interface TelemetryVelocityChartProps {
  data: TelemetryPoint[];
}

export const TelemetryVelocityChart: React.FC<TelemetryVelocityChartProps> = ({
  data,
}) => {
  const chartData = data.length > 0 ? data : [];

  if (chartData.length === 0) {
    return (
      <div className="h-[140px] w-full flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/10 bg-white/[0.01] text-slate-500">
        <span className="text-[11px] font-mono">No velocity data yet</span>
        <p className="text-[9px] text-slate-600">Event velocity appears after graph activity</p>
      </div>
    );
  }

  return (
    <div className="h-[140px] w-full relative pt-1">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={140}>
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
          <defs>
            <linearGradient id="gradientVelocity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.6} />
              <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.5} />
          <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 9 }} />
          <YAxis stroke="#64748b" tick={{ fontSize: 9 }} />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload;
                return (
                  <div className="bg-slate-900 border border-cyan-500/40 px-2.5 py-1.5 rounded text-[10px] font-mono text-cyan-300 shadow-xl backdrop-blur-md">
                    <p className="text-slate-400 font-bold">{item.time}</p>
                    <p className="text-cyan-400">Velocity: {item.velocity} ev/min</p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Area
            type="monotone"
            dataKey="velocity"
            stroke="#06b6d4"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#gradientVelocity)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
