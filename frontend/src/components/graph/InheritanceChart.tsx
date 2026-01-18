"use client";

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface ParentItem {
  id: string;
  fraction?: number;
}

interface InheritanceChartProps {
  parents: ParentItem[];
}

const COLORS = ['#22d3ee', '#8b5cf6', '#a855f7', '#ec4899', '#f43f5e'];

export function InheritanceChart({ parents }: InheritanceChartProps) {
  if (!parents || parents.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-md border border-dashed border-slate-800 text-[10px] text-slate-500">
        No parents (Root Node)
      </div>
    );
  }

  const data = parents.map((p, i) => ({
    name: p.id.slice(0, 8),
    value: p.fraction ?? (1 / parents.length),
    color: COLORS[i % COLORS.length]
  }));

  // Calculate total for normalization display if needed
  const total = data.reduce((acc, d) => acc + d.value, 0);

  return (
    <div className="h-40 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={55}
            paddingAngle={5}
            dataKey="value"
            animationDuration={1000}
            stroke="none"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#0f172a', 
              border: '1px solid #1e293b',
              borderRadius: '8px',
              fontSize: '10px',
              color: '#f1f5f9'
            }}
            itemStyle={{ color: '#22d3ee' }}
            formatter={(value: any) => {
              const val = typeof value === 'number' ? value : 0;
              return `${(val * 100 / (total || 1)).toFixed(1)}%`;
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-1 overflow-hidden">
            <div className="h-1.5 w-1.5 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
            <span className="truncate text-[9px] text-slate-400">{d.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
