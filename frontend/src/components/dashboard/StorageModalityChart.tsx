"use client";

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface StorageModalityChartProps {
  byType: Record<string, number>;
  totalBytes: number;
}

const COLORS = ["#06b6d4", "#10b981", "#a855f7", "#f59e0b", "#ec4899", "#64748b"];

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export const StorageModalityChart: React.FC<StorageModalityChartProps> = ({
  byType,
}) => {
  const chartData = Object.entries(byType).map(([type, count]) => ({
    name: type.toUpperCase(),
    count: count,
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex flex-col h-full w-full">
        <div className="h-[180px] w-full flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/10 bg-white/[0.01] text-slate-500">
          <span className="text-[11px] font-mono">No storage data yet</span>
          <p className="text-[9px] text-slate-600">File types appear after document ingestion</p>
        </div>
      </div>
    );
  }

  const displayData = chartData;

  return (
    <div className="flex flex-col h-full w-full">
      <div className="h-[180px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={displayData}
            margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
            <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-slate-900/95 border border-emerald-500/40 p-2.5 rounded-lg shadow-xl backdrop-blur-md text-[11px] font-mono">
                      <p className="text-emerald-400 font-bold mb-1">{data.name}</p>
                      <p className="text-slate-300">
                        Files: <span className="font-bold text-white">{data.count}</span>
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {displayData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
