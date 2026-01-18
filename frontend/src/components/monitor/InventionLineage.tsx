"use client";

import React, { useState, useEffect } from "react";
import { GitBranch, Info, Brain, Link as LinkIcon, Calendar, Percent } from "lucide-react";

interface ProvenanceNode {
  id: string;
  content: string;
  created_at: string;
}

interface InventionDetail {
  concept_id: string;
  title: string;
  description: string;
  content: string;
  confidence: number;
  node_id: string | null;
  created_at: string;
  provenance: ProvenanceNode[];
}

interface InventionLineageProps {
  graphId: string;
  conceptId: string | null;
}

export default function InventionLineage({ graphId, conceptId }: InventionLineageProps) {
  const [invention, setInvention] = useState<InventionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!conceptId) return;

    const fetchDetail = async () => {
      setIsLoading(true);
      try {
        const { getSession } = await import("next-auth/react");
        const session = await getSession();
        const headers: Record<string, string> = {};
        if (session && (session as any).accessToken) {
          headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
        }

        const res = await fetch(`/api/v1/graphs/${graphId}/inventions/${conceptId}`, { headers });
        if (res.ok) {
          const data = await res.json();
          setInvention(data);
        }
      } catch (err) {
        console.error("Failed to fetch invention detail:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDetail();
  }, [graphId, conceptId]);

  if (!conceptId) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900/20 border border-dashed border-slate-800 rounded-xl h-full text-slate-500 text-sm">
        <GitBranch className="h-8 w-8 mb-3 opacity-20" />
        <p>Select an invented concept to view its provenance tree</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 h-full">
        <div className="h-6 w-6 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!invention) return null;

  return (
    <div className="flex flex-col h-full bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden animate-in fade-in zoom-in-95 duration-500">
      {/* Detail Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/60">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-violet-500/20 text-violet-400">
              <Brain className="h-4 w-4" />
            </div>
            <h3 className="font-bold text-slate-100">{invention.title}</h3>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-400 font-medium">
             <Percent className="h-3 w-3" />
             {Math.round(invention.confidence * 100)}% RELIABILITY
          </div>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed italic">
          "{invention.description}"
        </p>
      </div>

      {/* Lineage Tree */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* The Synthesized Node */}
        <div className="relative pl-8">
           <div className="absolute left-0 top-1/2 -translate-y-1/2 w-6 h-0.5 bg-violet-500/30" />
           <div className="p-3 bg-violet-500/10 border border-violet-500/30 rounded-lg">
             <div className="text-[10px] text-violet-400 font-mono mb-1 uppercase tracking-tighter">Synthesized Output</div>
             <p className="text-xs text-slate-200 line-clamp-3 leading-normal">
               {invention.content}
             </p>
           </div>
        </div>

        {/* The Connection Lines */}
        <div className="flex flex-col items-center py-2 relative">
           <div className="w-px h-8 bg-gradient-to-b from-violet-500/30 to-slate-800" />
           <div className="text-[10px] text-slate-500 bg-slate-900 px-2 relative -top-4 font-mono">PROVENANCE SOURCE</div>
        </div>

        {/* Source Nodes */}
        <div className="grid grid-cols-1 gap-3">
          {invention.provenance.map((source, i) => (
            <div 
              key={source.id} 
              className="group relative flex flex-col p-3 bg-slate-800/40 border border-slate-700/50 rounded-lg hover:border-slate-600 transition-colors"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
                  <LinkIcon className="h-3 w-3" />
                  NODE:{source.id.slice(0, 8)}
                </div>
                <div className="flex items-center gap-1 text-[9px] text-slate-600">
                  <Calendar className="h-3 w-3" />
                  {source.created_at ? new Date(source.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : "N/A"}
                </div>
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-2 leading-normal group-hover:text-slate-300 transition-colors">
                {source.content}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="px-4 py-2 bg-slate-900/60 border-t border-slate-800 flex items-center gap-2 text-[10px] text-slate-500">
        <Info className="h-3 w-3" />
        <span>Invention based on {invention.provenance.length} distinct knowledge fragments.</span>
      </div>
    </div>
  );
}
