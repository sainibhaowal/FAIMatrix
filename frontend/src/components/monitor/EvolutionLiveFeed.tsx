"use client";

import React, { useState, useEffect, useRef } from "react";
import { Terminal, Activity, Zap, Trash2, GitMerge, RefreshCw } from "lucide-react";

interface EvolutionAction {
  graph_id: string;
  region_id: string;
  kind: "merge" | "prune" | "promote" | string;
  details: string;
  timestamp: number;
}

export default function EvolutionLiveFeed() {
  const [logs, setLogs] = useState<EvolutionAction[]>([]);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async () => {
    try {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers: Record<string, string> = {};
      if (session && (session as any).accessToken) {
        headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const res = await fetch("/api/ops/evolution/logs?limit=50", { headers });
      if (res.ok) {
        const data = await res.json();
        setLogs(prev => {
          // Only update if we have new data
          if (JSON.stringify(data) === JSON.stringify(prev)) return prev;
          return data;
        });
      }
    } catch (err) {
      console.error("Failed to fetch evolution logs:", err);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (isAutoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isAutoScroll]);

  const getIcon = (kind: string) => {
    switch (kind) {
      case "merge":
        return <GitMerge className="h-3 w-3 text-emerald-400" />;
      case "prune":
        return <Trash2 className="h-3 w-3 text-rose-400" />;
      case "promote":
        return <Zap className="h-3 w-3 text-amber-400" />;
      default:
        return <Activity className="h-3 w-3 text-slate-400" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-violet-400" />
          <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
            Evolution Live Feed
          </h3>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] text-slate-500 font-mono">LIVE</span>
          </div>
          <button 
            onClick={() => setIsAutoScroll(!isAutoScroll)}
            className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors ${
              isAutoScroll 
                ? "bg-violet-500/10 border-violet-500/30 text-violet-400" 
                : "bg-slate-800 border-slate-700 text-slate-500"
            }`}
          >
            {isAutoScroll ? "AUTO-SCROLL ON" : "AUTO-SCROLL OFF"}
          </button>
        </div>
      </div>

      {/* Terminal View */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-[11px] leading-relaxed"
      >
        {logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-600 gap-2">
            <RefreshCw className="h-5 w-5 animate-spin opacity-20" />
            <p>Awaiting autonomic system signals...</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {logs.map((log, i) => (
              <div key={`${log.timestamp}-${i}`} className="group flex items-start gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
                <span className="text-slate-600 shrink-0">
                  {new Date(log.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
                </span>
                <span className="flex items-center gap-1 shrink-0 w-20">
                  {getIcon(log.kind)}
                  <span className={`font-bold uppercase ${
                    log.kind === "merge" ? "text-emerald-500/80" : 
                    log.kind === "prune" ? "text-rose-500/80" : 
                    log.kind === "promote" ? "text-amber-500/80" : "text-slate-500"
                  }`}>
                    {log.kind}
                  </span>
                </span>
                <span className="text-slate-300 line-clamp-1 group-hover:line-clamp-none transition-all">
                  {log.details}
                  <span className="ml-2 text-[9px] text-slate-600 opacity-60">
                    [reg:{log.region_id.split('#')[0].slice(-6)}]
                  </span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer / Stats */}
      <div className="px-4 py-1.5 bg-slate-900/40 border-t border-slate-800/50 flex justify-between items-center text-[9px] text-slate-500 font-mono">
        <span>BUFFER: {logs.length}/50 ACTIONS</span>
        <span>SYSTEM VERSION: FAIM-EVO-CORE/3.0</span>
      </div>
    </div>
  );
}
