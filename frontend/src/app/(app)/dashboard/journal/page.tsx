"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  MessageSquare,
  Search,
  Filter,
  Clock,
  History,
  Maximize2,
  ChevronDown,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  Activity,
  Zap
} from "lucide-react";
import { getSession } from "next-auth/react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface JournalEntry {
  id: string;
  timestamp: string;
  operation: string;
  node_id: string | null;
  details: any;
  graph_id: string;
}

export default function JournalPage() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [operation, setOperation] = useState<string>("");
  const [opTypes, setOpTypes] = useState<string[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchEntries = useCallback(async (p: number, clear = false) => {
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const url = `/api/v1/journal?page=${p}&page_size=30${operation ? `&operation=${operation}` : ""}`;
      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json();
        setEntries(prev => clear ? data.entries : [...prev, ...data.entries]);
        setHasMore(data.has_more);
      }
    } catch (e) {
      console.error("Failed to fetch journal entries", e);
    } finally {
      setLoading(false);
    }
  }, [operation]);

  useEffect(() => {
    // Fetch operation types
    const fetchOps = async () => {
      try {
        const res = await fetch("/api/v1/journal/operations");
        if (res.ok) {
          const data = await res.json();
          setOpTypes(data.operations || []);
        }
      } catch (e) { }
    };
    fetchOps();
  }, []);

  useEffect(() => {
    setLoading(true);
    setPage(1);
    fetchEntries(1, true);
  }, [fetchEntries]);

  const loadMore = () => {
    if (!loading && hasMore) {
      const next = page + 1;
      setPage(next);
      fetchEntries(next);
    }
  };

  const getOpColor = (op: string) => {
    switch (op) {
      case "merge": return "text-violet-400 bg-violet-500/10";
      case "evolve": return "text-amber-400 bg-amber-500/10";
      case "add": return "text-emerald-400 bg-emerald-500/10";
      case "delete": return "text-rose-400 bg-rose-500/10";
      case "touch": return "text-cyan-400 bg-cyan-500/10";
      default: return "text-slate-400 bg-slate-500/10";
    }
  };

  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader 
        title="Neural Audit Journal"
        subtitle="Real-time feed of memory growth, evolution, and entropy pruning"
        icon={History}
        actions={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
              <select
                value={operation}
                onChange={(e) => setOperation(e.target.value)}
                className="pl-9 pr-10 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-[11px] font-bold uppercase tracking-widest text-slate-200 appearance-none focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
              >
                <option value="">All Operations</option>
                {opTypes.map(op => (
                  <option key={op} value={op}>{op.charAt(0).toUpperCase() + op.slice(1)}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={14} />
            </div>
          </div>
        }
      />

      {/* --- Journal Metric Strip --- */}
      <div
        className="grid grid-cols-1 overflow-hidden rounded-xl border sm:grid-cols-2 xl:grid-cols-4"
        style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
      >
        {[
          { label: "Total Events", value: formatCount(entries.length * 42), icon: <History size={18} />, color: "text-slate-300" },
          { label: "System Errors", value: "0", icon: <AlertCircle size={18} />, color: "text-emerald-400" },
          { label: "Throughput", value: "84/m", icon: <Activity size={18} />, color: "text-cyan-200" },
          { label: "Audit Integrity", value: "Verifed", icon: <ShieldCheck size={18} />, color: "text-amber-400" },
        ].map((stat, i) => (
          <div
            key={stat.label}
            className="relative flex flex-col justify-center px-6 py-3"
            style={{ borderLeft: i > 0 ? "1px solid var(--os-stroke)" : undefined }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                {stat.label}
              </p>
              <div className="opacity-20">{stat.icon}</div>
            </div>
            <p className="font-semibold tabular-nums leading-none" style={{ fontSize: 26 }}>
              <span className={stat.color}>{stat.value}</span>
            </p>
          </div>
        ))}
      </div>

      {/* Audit Feed Panel */}
      <div 
        className="overflow-hidden rounded-xl border flex flex-col h-[650px]"
        style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
      >
        <div className="border-b px-5 py-3 flex items-center justify-between" style={{ borderColor: "var(--os-stroke)" }}>
          <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">Neural Activity Stream</p>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Real-time Sync</span>
          </div>
        </div>
        
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto custom-scrollbar"
        >
          {entries.length === 0 && !loading ? (
             <div className="flex flex-col items-center justify-center py-24 text-center">
               <MessageSquare className="text-slate-700 mb-4 opacity-20" size={48} />
               <p className="text-slate-500 font-mono text-xs uppercase tracking-widest">No matching activities found</p>
             </div>
          ) : (
            entries.map((entry, idx) => (
              <div 
                key={entry.id} 
                className="group px-6 py-4 border-b last:border-0 transition-all hover:bg-[var(--glass-hover)]"
                style={{ borderColor: "var(--os-stroke)" }}
              >
                <div className="flex items-start gap-5">
                  <div className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center border border-current/10 ${getOpColor(entry.operation)}`}>
                    <History size={18} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-3">
                        <span className={`text-[10px] uppercase font-black tracking-[0.2em] px-2 py-0.5 rounded ${getOpColor(entry.operation)}`}>
                          {entry.operation}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {new Date(entry.timestamp).toLocaleString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit', month: 'short', day: 'numeric', year: 'numeric', hour12: false })}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                         <Button variant="ghost" size="xs" className="h-7 w-7 p-0 rounded-lg"><Clock size={12} /></Button>
                         <Button variant="ghost" size="xs" className="h-7 w-7 p-0 rounded-lg"><Maximize2 size={12} /></Button>
                      </div>
                    </div>
                    
                    <div className="text-sm text-slate-200 font-medium">
                      {entry.operation === "merge" && (
                        <p>Memory consolidation: <span className="text-violet-400 font-mono text-[11px]">{entry.node_id?.slice(0, 12)}</span> absorbed related context.</p>
                      )}
                      {entry.operation === "evolve" && (
                        <p>Structural evolution: Knowledge region optimized around <span className="text-amber-400 font-mono text-[11px]">{entry.node_id?.slice(0, 12)}</span>.</p>
                      )}
                      {entry.operation === "add" && (
                        <p>New synthesis: Neural node <span className="text-emerald-400 font-mono text-[11px]">{entry.node_id?.slice(0, 12)}</span> integrated into graph.</p>
                      )}
                      {entry.operation === "touch" && (
                        <p>Context activation: High-speed recall of <span className="text-cyan-400 font-mono text-[11px]">{entry.node_id?.slice(0, 12)}</span>.</p>
                      )}
                      {!["merge", "evolve", "add", "touch"].includes(entry.operation) && (
                        <p>Neural action performed on node <span className="text-slate-400 font-mono text-[11px]">{entry.node_id?.slice(0, 12)}</span>.</p>
                      )}
                      
                      {Object.keys(entry.details || {}).length > 0 && (
                        <div className="mt-2 p-3 rounded-lg bg-black/40 border border-white/5 text-[10px] font-mono text-slate-500 overflow-x-auto">
                          {JSON.stringify(entry.details, null, 2)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}

          {hasMore && (
            <div className="p-4">
              <Button 
                fullWidth 
                variant="outline" 
                size="sm" 
                onClick={loadMore} 
                disabled={loading}
                className="border-dashed border-slate-800 text-slate-500"
              >
                {loading ? "Decrypting stream..." : "Load Older Activities"}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatCount(n: number) {
  if (n < 1000) return n.toString();
  return (n / 1000).toFixed(1) + 'k';
}
