"use client";

import React from "react";
import { MessageSquare, Trash2, Edit3, MoreVertical, Clock } from "lucide-react";
import { Button } from "@/components/ui/Button";

const MOCK_HISTORY = [
  { id: "h1", title: "Region U:621b Optimization", date: "2h ago" },
  { id: "h2", title: "Vector Density Analysis", date: "5h ago" },
  { id: "h3", title: "Tenant Access Logs Hub", date: "1d ago" },
  { id: "h4", title: "Entropy Pruning Protocol", date: "2d ago" },
  { id: "h5", title: "Structural Integrity Check", date: "3d ago" },
];

export function HistoryPanel() {
  return (
    <div 
      className="flex flex-col h-full overflow-hidden bg-transparent" 
    >
      {/* Precision Header */}
      <div className="px-5 py-3 border-b flex items-center justify-between" style={{ borderColor: 'var(--os-stroke)', background: 'rgba(255,255,255,0.02)' }}>
        <div className="flex items-center gap-2.5">
          <Clock size={14} className="text-primary-400" />
          <h2 className="text-[10px] font-black uppercase tracking-[0.25em] text-white">Neural Threads</h2>
        </div>
        <button className="text-slate-600 hover:text-primary-300 transition-colors p-1">
          <MoreVertical size={14} />
        </button>
      </div>

      {/* List Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-0.5">
        {MOCK_HISTORY.map((item) => (
          <div
            key={item.id}
            className="group relative flex flex-col gap-0.5 px-3 py-2.5 rounded-xl transition-all duration-200 hover:bg-white/[0.04] border border-transparent hover:border-white/5 cursor-pointer"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="text-[12px] font-semibold text-slate-300 line-clamp-1 leading-none tracking-tight transition-colors group-hover:text-white">
                {item.title}
              </span>
              <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5 shrink-0 translate-y-[-2px]">
                <button className="h-5 w-5 flex items-center justify-center rounded-md hover:bg-white/10 text-slate-500 hover:text-white transition-all">
                  <Edit3 size={10} />
                </button>
                <button className="h-5 w-5 flex items-center justify-center rounded-md hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 transition-all">
                  <Trash2 size={10} />
                </button>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
               <span className="text-[8px] font-black font-mono text-slate-600 uppercase tracking-widest">{item.date}</span>
               <div className="h-0.5 w-0.5 rounded-full bg-slate-800" />
               <span className="text-[8px] font-black text-slate-700 uppercase tracking-[0.2em]">Context:8.4</span>
            </div>
          </div>
        ))}
      </div>

      {/* Footer System */}
      <div className="p-4 border-t bg-black/20" style={{ borderColor: 'var(--os-stroke)' }}>
        <Button 
          variant="outline" 
          fullWidth 
          size="sm" 
          className="h-8 text-[9px] font-black uppercase tracking-[0.3em] border-white/5 bg-white/5 hover:bg-white/10 hover:border-white/10 transition-all"
        >
          Purge Buffer
        </Button>
      </div>
    </div>
  );
}
