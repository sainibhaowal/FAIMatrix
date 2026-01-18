"use client";

import React, { useEffect, useState } from "react";
import { 
  X, 
  Clock, 
  GitCommit, 
  CornerDownRight,
  ChevronRight,
  Database
} from "lucide-react";
import { getSession } from "next-auth/react";

interface TimelineEntry {
  id: string;
  timestamp: string;
  operation: string;
  details: any;
}

interface NodeTimelineDrawerProps {
  nodeId: string | null;
  onClose: () => void;
}

export function NodeTimelineDrawer({ nodeId, onClose }: NodeTimelineDrawerProps) {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!nodeId) return;

    const fetchTimeline = async () => {
      setLoading(true);
      try {
        const session = await getSession();
        const token = (session as any)?.accessToken;
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`/api/v1/journal/node/${nodeId}/timeline`, { headers });
        if (res.ok) {
          const data = await res.json();
          setEntries(data || []);
        }
      } catch (e) {
        console.error("Failed to fetch node timeline", e);
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [nodeId]);

  if (!nodeId) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-slate-950 border-l border-slate-800 shadow-2xl z-[100] animate-[slideInRight_0.3s_cubic-bezier(0.16,1,0.3,1)]">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
               <Clock size={18} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100">Memory History</h3>
              <p className="text-[10px] text-slate-500 font-mono">{nodeId.slice(0, 16)}...</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-xl transition-all"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
          {loading ? (
            <div className="space-y-4">
               {[1,2,3,4].map(i => (
                 <div key={i} className="flex gap-4">
                    <div className="w-4 h-4 rounded-full bg-slate-800 animate-pulse mt-1" />
                    <div className="flex-1 space-y-2">
                       <div className="h-4 bg-slate-800 rounded animate-pulse w-1/3" />
                       <div className="h-10 bg-slate-800/40 rounded animate-pulse" />
                    </div>
                 </div>
               ))}
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center py-20">
               <Database className="mx-auto text-slate-800 mb-4" size={32} />
               <p className="text-xs text-slate-500">No history found for this node.</p>
            </div>
          ) : (
            <div className="relative space-y-8">
              {/* Vertical line */}
              <div className="absolute left-[7px] top-2 bottom-2 w-px bg-slate-800" />

              {entries.map((entry) => (
                <div key={entry.id} className="relative flex gap-6 group">
                  {/* Dot */}
                  <div className={`mt-1.5 w-4 h-4 rounded-full border-2 border-slate-950 z-10 ${
                    entry.operation === 'add' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' :
                    entry.operation === 'merge' ? 'bg-violet-500' :
                    entry.operation === 'evolve' ? 'bg-amber-500' : 'bg-slate-600'
                  }`} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                        {entry.operation}
                      </span>
                      <span className="text-[10px] text-zinc-500">
                        {new Date(entry.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })}
                      </span>
                    </div>
                    
                    <div className="p-3 rounded-xl bg-slate-900 border border-slate-800/50 group-hover:border-slate-700 transition-colors">
                      <div className="text-xs text-slate-400 leading-relaxed">
                        {entry.operation === 'add' && "Initial memory encoding and linkage."}
                        {entry.operation === 'merge' && "Merged with another context vector."}
                        {entry.operation === 'evolve' && "Node hierarchy weight updated."}
                        {entry.operation === 'touch' && "Retrieved and refreshed."}
                      </div>
                      
                      {/* JSON details mini-view */}
                      <button className="mt-2 text-[10px] text-cyan-500 hover:text-cyan-400 flex items-center gap-1 group/btn">
                        View Metadata <ChevronRight size={10} className="group-hover/btn:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-900/40 border-t border-slate-800">
           <button 
             className="w-full py-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 text-xs font-semibold hover:bg-cyan-500/20 transition-all flex items-center justify-center gap-2 border border-cyan-500/20"
           >
              Export Lineage <GitCommit size={14} />
           </button>
        </div>
      </div>
    </div>
  );
}
