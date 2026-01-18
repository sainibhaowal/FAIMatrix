"use client";

import React, { useEffect, useState } from "react";
import { Tooltip } from "@/components/ui/Tooltip";
import { getSession } from "next-auth/react";

interface HeatmapData {
  [date: string]: number;
}

export function NeuralActivityHeatmap() {
  const [data, setData] = useState<HeatmapData>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const session = await getSession();
        const token = (session as any)?.accessToken;
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/v1/journal/stats", { headers });
        if (res.ok) {
          const stats = await res.json();
          setData(stats.daily_activity || {});
        }
      } catch (e) {
        console.error("Failed to fetch journal stats for heatmap", e);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  // Generate last 30 days
  const days = Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return d.toISOString().split("T")[0];
  });

  const getIntensity = (count: number) => {
    if (count === 0) return "bg-slate-800/40";
    if (count < 5) return "bg-emerald-500/20";
    if (count < 15) return "bg-emerald-500/40";
    if (count < 30) return "bg-emerald-500/60";
    return "bg-emerald-500/90 shadow-[0_0_8px_rgba(16,185,129,0.4)]";
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xs font-semibold text-slate-100 uppercase tracking-wider">
            Neural Growth Map
          </h3>
          <p className="text-[10px] text-slate-500">Activity density over the last 30 days</p>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
          <span>Less</span>
          <div className="flex gap-1">
            <div className="w-2 h-2 rounded-sm bg-slate-800/40" />
            <div className="w-2 h-2 rounded-sm bg-emerald-500/20" />
            <div className="w-2 h-2 rounded-sm bg-emerald-500/50" />
            <div className="w-2 h-2 rounded-sm bg-emerald-500/90" />
          </div>
          <span>More</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {days.map((day) => {
          const count = data[day] || 0;
          return (
            <Tooltip 
              key={day}
              content={
                <div className="text-[10px]">
                  <p className="font-medium">{new Date(day).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</p>
                  <p className="text-emerald-400">{count} engine operations</p>
                </div>
              }
            >
              <div
                className={`w-3 h-3 rounded-[2px] cursor-help transition-all duration-300 hover:scale-125 ${getIntensity(
                  count
                )}`}
              />
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
