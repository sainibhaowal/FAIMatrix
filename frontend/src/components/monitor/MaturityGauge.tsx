"use client";

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface MaturityGaugeProps {
  value: number;
  min: number;
  max: number;
  label: string;
  target?: number;
  color?: string;
  unit?: string;
}

export function MaturityGauge({ 
  value, 
  min, 
  max, 
  label, 
  target, 
  color = "#22d3ee",
  unit = ""
}: MaturityGaugeProps) {
  // Normalize value for PieChart (0 to 1)
  const clampedValue = Math.min(max, Math.max(min, value));
  const percent = (clampedValue - min) / (max - min);
  
  const data = [
    { name: 'Value', value: percent },
    { name: 'Remain', value: 1 - percent }
  ];

  return (
    <div className="flex flex-col items-center">
      <div className="h-28 w-40 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="80%"
              startAngle={180}
              endAngle={0}
              innerRadius={50}
              outerRadius={65}
              paddingAngle={0}
              dataKey="value"
              stroke="none"
              animationDuration={1500}
            >
              <Cell fill={color} />
              <Cell fill="#1e293b" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
          <span className="text-lg font-bold text-slate-100">{value.toFixed(2)}{unit}</span>
          <span className="text-[9px] uppercase tracking-wider text-slate-500">{label}</span>
        </div>
        {target !== undefined && (
          <div 
            className="absolute h-4 w-0.5 bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]"
            style={{ 
              left: '50%', 
              bottom: '15%', 
              transform: `translateX(-50%) rotate(${((target - min) / (max - min)) * 180 - 90}deg)`,
              transformOrigin: 'bottom center'
            }}
          />
        )}
      </div>
      {target !== undefined && (
        <div className="mt-1 text-[9px] text-slate-500">
          Target: <span className="text-slate-300">{target.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
}
