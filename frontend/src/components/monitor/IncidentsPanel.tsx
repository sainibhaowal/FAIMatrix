"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, Info, AlertCircle } from "lucide-react";

interface Incident {
  id: string;
  level: string;
  message: string;
  source: string;
  timestamp: string;
}

function formatTime(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return d.toLocaleDateString();
}

const LEVEL_STYLES: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  error: { icon: AlertCircle, color: "text-rose-400", bg: "bg-rose-500/10" },
  warning: { icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/10" },
  info: { icon: Info, color: "text-cyan-400", bg: "bg-cyan-500/10" },
  success: { icon: CheckCircle, color: "text-emerald-400", bg: "bg-emerald-500/10" },
};

export function IncidentsPanel() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/ops/incidents")
      .then((r) => r.json())
      .then((data) => {
        setIncidents(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const style = (level: string) => LEVEL_STYLES[level] || LEVEL_STYLES.info;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
          <AlertTriangle size={14} className="text-amber-400" />
          Incidents
        </h3>
        <span className="text-[10px] text-slate-500">{incidents.length} total</span>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-slate-800/50 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : incidents.length === 0 ? (
        <div className="text-center py-6 text-[11px] text-slate-500">
          <CheckCircle size={20} className="mx-auto mb-2 text-emerald-400" />
          No incidents reported
        </div>
      ) : (
        <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1">
          {incidents.map((inc) => {
            const s = style(inc.level);
            const Icon = s.icon;
            return (
              <div
                key={inc.id}
                className={`rounded-lg border border-slate-800 ${s.bg} p-3`}
              >
                <div className="flex items-start gap-2">
                  <Icon size={14} className={`${s.color} mt-0.5 shrink-0`} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] text-slate-200 leading-relaxed">
                      {inc.message}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500">
                      <span>{inc.source}</span>
                      <span>•</span>
                      <span>{formatTime(inc.timestamp)}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
