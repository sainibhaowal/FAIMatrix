"use client";

import React, { useEffect, useState } from "react";
import { Shield, User, Clock } from "lucide-react";

interface AuditEntry {
  id: string;
  ts: string;
  action: string;
  target_type: string;
  actor_user_id: string | null;
  outcome: string;
}

function formatTime(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatAction(action: string): string {
  return action.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function AuditPanel() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/ops/audit?limit=20")
      .then((r) => r.json())
      .then((data) => {
        setLogs(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
          <Shield size={14} className="text-emerald-400" />
          Audit Log
        </h3>
        <span className="text-[10px] text-slate-500">{logs.length} entries</span>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-slate-800/50 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-6 text-[11px] text-slate-500">
          No audit logs yet
        </div>
      ) : (
        <div className="space-y-2 max-h-[240px] overflow-y-auto pr-1">
          {logs.map((log) => (
            <div
              key={log.id}
              className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-200">
                  {formatAction(log.action)}
                </span>
                <span
                  className={`text-[10px] ${
                    log.outcome === "success"
                      ? "text-emerald-400"
                      : "text-rose-400"
                  }`}
                >
                  {log.outcome}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500">
                <span className="flex items-center gap-1">
                  <User size={10} />
                  {log.actor_user_id?.slice(0, 8) || "system"}
                </span>
                <span className="flex items-center gap-1">
                  <Clock size={10} />
                  {formatTime(log.ts)}
                </span>
                <span>{log.target_type}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
