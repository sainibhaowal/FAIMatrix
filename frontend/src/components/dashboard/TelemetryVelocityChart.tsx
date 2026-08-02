"use client";

import React from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";

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
  const chartData =
    data.length > 0
      ? data
      : [
          { seq: 1, time: "10s ago", velocity: 2 },
          { seq: 2, time: "8s ago", velocity: 5 },
          { seq: 3, time: "6s ago", velocity: 3 },
          { seq: 4, time: "4s ago", velocity: 8 },
          { seq: 5, time: "2s ago", velocity: 4 },
          { seq: 6, time: "now", velocity: 6 },
        ];

  return (
    <div className="h-10 w-full relative">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
          <defs>
            <linearGradient id="gradientVelocity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.6} />
              <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload;
                return (
                  <div className="bg-slate-900 border border-cyan-500/40 px-2 py-1 rounded text-[10px] font-mono text-cyan-300 shadow">
                    {item.time}: {item.velocity} ev/min
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
            strokeWidth={1.5}
            fillOpacity={1}
            fill="url(#gradientVelocity)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
