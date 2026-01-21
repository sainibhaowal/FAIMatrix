"use client";

import React, { useEffect, useState } from "react";
import { buildFaimHeaders } from "@/lib/api-client";
import { Sparkles, AlertCircle, Bookmark, ChevronRight } from "lucide-react";

interface Insight {
  insight_id: string;
  title: string;
  description: string;
  insight_type: string;
  surprise_score: number;
  related_nodes: string[];
  evidence: string;
}

interface InsightFeedPanelProps {
  graphId: string;
}

const InsightFeedPanel: React.FC<InsightFeedPanelProps> = ({ graphId }) => {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchInsights() {
      try {
        setLoading(true);
        const { getSession } = await import("next-auth/react");
        const session = await getSession();
        const headers = buildFaimHeaders();
        if (session && (session as any).accessToken) {
          (headers as any)["Authorization"] = `Bearer ${(session as any).accessToken}`;
        }

        const res = await fetch(`/api/ops/graphs/${graphId}/insights`, {
          headers,
        });
        if (!res.ok) throw new Error("Failed to load insights");
        const data = await res.json();
        if (!cancelled) setInsights(data);
      } catch (err) {
        if (!cancelled) setError("Discovery engine offline or no insights yet.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchInsights();
    const interval = setInterval(fetchInsights, 30000); // Poll every 30s

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [graphId]);

  if (loading && insights.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 space-y-4">
        <Sparkles className="w-8 h-8 text-cyan-500 animate-pulse" />
        <p className="text-xs text-slate-400 font-medium">Scanning for latent connections...</p>
      </div>
    );
  }

  if (error && insights.length === 0) {
    return (
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/50 text-center">
        <AlertCircle className="w-5 h-5 text-slate-500 mx-auto mb-2" />
        <p className="text-[11px] text-slate-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col space-y-4 p-1">
      <header className="px-2">
        <h2 className="text-xs font-bold text-slate-100 uppercase tracking-widest flex items-center gap-2">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          Intelligence Feed
        </h2>
        <p className="text-[10px] text-slate-500 mt-1">
          FAIM has detected {insights.length} surprising patterns in your mental model.
        </p>
      </header>

      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-3">
        {insights.map((insight) => (
          <div 
            key={insight.insight_id}
            className="group relative p-3 rounded-xl border border-slate-800 bg-slate-900/40 hover:border-cyan-500/30 transition-all duration-300"
          >
            <div className="flex items-start justify-between mb-2">
               <div className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-tighter ${
                 insight.insight_type === 'surprise' ? 'bg-cyan-500/10 text-cyan-400' : 'bg-amber-500/10 text-amber-400'
               }`}>
                 {insight.insight_type}
               </div>
               <div className="text-[10px] font-mono text-slate-600">
                 SCORE: {(insight.surprise_score * 100).toFixed(0)}
               </div>
            </div>

            <h3 className="text-[11px] font-bold text-slate-200 group-hover:text-cyan-400 transition-colors mb-1">
              {insight.title}
            </h3>
            
            <p className="text-[10px] text-slate-400 leading-relaxed mb-3">
              {insight.description}
            </p>

            <div className="p-2 rounded bg-slate-950/60 border border-slate-800/50">
               <div className="flex items-center gap-1.5 mb-1">
                 <Bookmark className="w-2.5 h-2.5 text-slate-500" />
                 <span className="text-[9px] font-bold text-slate-500 uppercase">Evidence</span>
               </div>
               <p className="text-[9px] text-slate-500 italic line-clamp-2 italic">
                 &quot;{insight.evidence}&quot;
               </p>
            </div>

            <button className="mt-3 w-full py-1.5 rounded-lg border border-slate-800 bg-slate-900/50 text-[10px] font-bold text-slate-400 hover:text-cyan-400 hover:border-cyan-500/20 flex items-center justify-center gap-1 transition-all">
              Inspect Connection
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default InsightFeedPanel;
