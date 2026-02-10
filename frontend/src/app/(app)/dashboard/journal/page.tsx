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
  ArrowRight
} from "lucide-react";
import { getSession } from "next-auth/react";

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
      } catch (e) {}
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
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-3">
            <MessageSquare className="text-cyan-400" />
            Neural Audit Journal
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time feed of memory growth, evolution, and entropy pruning.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
            <select 
              value={operation}
              onChange={(e) => setOperation(e.target.value)}
              className="pl-9 pr-8 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 appearance-none focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
            >
              <option value="">All Operations</option>
              {opTypes.map(op => (
                <option key={op} value={op}>{op.charAt(0).toUpperCase() + op.slice(1)}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={14} />
          </div>
        </div>
      </div>

      {/* Feed Container */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar"
      >
        {entries.map((entry, idx) => (
          <div 
            key={entry.id}
            className="group relative flex gap-4 p-4 rounded-2xl border border-slate-800/60 bg-slate-900/20 backdrop-blur-sm transition-all duration-300 hover:bg-slate-900/40 hover:border-slate-700/60"
          >
            {/* Timeline element */}
            <div className="absolute left-[34px] top-12 bottom-0 w-px bg-slate-800 group-last:hidden" />
            
            {/* Icon */}
            <div className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center border border-current/10 ${getOpColor(entry.operation)}`}>
               <History size={18} />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded-md ${getOpColor(entry.operation)}`}>
                    {entry.operation}
                  </span>
                  <span className="text-xs text-slate-500">
                    {new Date(entry.timestamp).toLocaleString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit', month: 'short', day: 'numeric', year: 'numeric', hour12: false })}
                  </span>
                </div>
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                   <button 
                     title="View Node Timeline"
                     className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-500 hover:text-cyan-400 transition-colors"
                   >
                     <Clock size={14} />
                   </button>
                   <button 
                     title="Expand Details"
                     className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-500 hover:text-slate-200 transition-colors"
                   >
                     <Maximize2 size={14} />
                   </button>
                </div>
              </div>

              <div className="text-sm text-slate-300">
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
              </div>

              {/* Dynamic Details (JSON-ish preview) */}
              {Object.keys(entry.details || {}).length > 0 && (
                <div className="mt-3 p-3 rounded-xl bg-black/20 border border-slate-800/40 text-[11px] font-mono text-slate-500 overflow-x-auto">
                  {JSON.stringify(entry.details, null, 2)}
                </div>
              )}
            </div>
          </div>
        ))}

        {hasMore && (
          <button 
            onClick={loadMore}
            disabled={loading}
            className="w-full py-4 mt-2 rounded-2xl border border-dashed border-slate-800 text-slate-500 text-xs font-semibold hover:bg-slate-900/20 hover:text-slate-300 transition-all flex items-center justify-center gap-2"
          >
            {loading ? "Decrypting..." : (
              <>
                Load Earlier Events <ChevronDown size={14} />
              </>
            )}
          </button>
        )}

        {!hasMore && entries.length > 0 && (
          <div className="text-center py-10 text-slate-600 text-[10px] uppercase tracking-widest">
            End of Neural Stream
          </div>
        )}

        {entries.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-full bg-slate-900 flex items-center justify-center mb-4 border border-slate-800">
              <MessageSquare className="text-slate-700" size={24} />
            </div>
            <h3 className="text-slate-400 font-semibold italic">Empty Journal</h3>
            <p className="text-slate-500 text-xs max-w-xs mt-1">
              No neural events have been recorded for this criteria yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
