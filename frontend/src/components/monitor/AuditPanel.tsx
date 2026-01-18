"use client";

import React, { useEffect, useState } from "react";
import { Shield, ArrowRight, History } from "lucide-react";
import Link from "next/link";
import { getSession } from "next-auth/react";

interface JournalEntry {
  id: string;
  timestamp: string;
  operation: string;
  node_id: string | null;
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
  const [logs, setLogs] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const session = await getSession();
        const token = (session as any)?.accessToken;
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/v1/journal?page_size=5", { headers });
        if (res.ok) {
          const data = await res.json();
          setLogs(data.entries || []);
        }
      } catch (e) {
        console.error("Failed to fetch audit logs", e);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
          <Shield size={14} className="text-emerald-400" />
          Neural Journal
        </h3>
        <Link 
          href="/dashboard/journal"
          className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors group"
        >
          View Full <ArrowRight size={10} className="group-hover:translate-x-0.5 transition-transform" />
        </Link>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-slate-800/50 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-6 text-[11px] text-slate-500">
          No neural events yet
        </div>
      ) : (
        <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
          {logs.map((log) => (
            <div
              key={log.id}
              className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                   <History size={10} className="text-slate-500" />
                   <span className="text-[11px] text-slate-200">
                     {formatAction(log.operation)}
                   </span>
                </div>
                <span className="text-[9px] text-slate-500">
                  {formatTime(log.timestamp)}
                </span>
              </div>
              <div className="mt-1 text-[10px] text-slate-500 font-mono">
                Node: {log.node_id?.slice(0, 12) || "N/A"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
