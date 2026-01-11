"use client";

import React, { useEffect, useState } from "react";
import { Server } from "lucide-react";

export function HealthCards() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/ops/health")
      .then((res) => res.json())
      .then(setHealth)
      .catch((_) => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-xs text-slate-500 animate-pulse">Checking system health...</div>;

  return (
    <div className="grid grid-cols-3 gap-3">
      {["db", "redis", "auth_provider"].map((sys) => (
        <section
          key={sys}
          className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 flex items-center justify-between"
        >
          <div className="flex items-center gap-2 capitalize font-medium text-xs text-slate-200">
            <Server size={14} className="text-slate-500" /> {sys}
          </div>
          <div
            className={`flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider ${
              health?.[sys] === "healthy"
                ? "text-emerald-400"
                : health?.[sys] === "offline"
                ? "text-amber-400"
                : "text-red-400"
            }`}
          >
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                health?.[sys] === "healthy"
                  ? "bg-emerald-400"
                  : health?.[sys] === "offline"
                  ? "bg-amber-400"
                  : "bg-red-400"
              }`}
            />
            {health?.[sys] || "unknown"}
          </div>
        </section>
      ))}
    </div>
  );
}
