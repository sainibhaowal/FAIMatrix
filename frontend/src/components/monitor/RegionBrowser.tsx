"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Network, Search, Layers, ChevronRight, Hash } from "lucide-react";
import { useUserIds } from "@/contexts/UserContext";
import { getSession } from "next-auth/react";

interface Region {
  id: string;
  label: string;
  node_count: number;
  density: number;
  top_terms: string[];
}

export function RegionBrowser() {
  const { graphId } = useUserIds();
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!graphId) return;

    const fetchRegions = async () => {
      try {
        const session = await getSession();
        const headers: Record<string, string> = {};
        if (session && (session as any).accessToken) {
          headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
        }

        const res = await fetch(`/api/v1/graphs/${encodeURIComponent(graphId)}/regions`, { headers });
        if (res.ok) {
          const data = await res.json();
          if (data.regions) {
            setRegions(data.regions);
            if (data.regions.length > 0) setSelectedId(data.regions[0].id);
          }
        }
      } catch (e) {
        console.error("Failed to fetch regions", e);
      } finally {
        setLoading(false);
      }
    };

    fetchRegions();
  }, [graphId]);

  if (loading) {
    return (
      <div className="h-64 bg-slate-800/20 rounded-2xl animate-pulse" />
    );
  }

  const selectedRegion = regions.find(r => r.id === selectedId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-cyan-500/20 rounded-lg text-cyan-400">
            <Layers size={18} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 italic">
              Semantic Region Browser
            </h3>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
              Automatically Discovered Knowledge Clusters
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Region List */}
        <div className="space-y-2 max-h-64 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-800">
          {regions.map((region) => (
            <button
              key={region.id}
              onClick={() => setSelectedId(region.id)}
              className={[
                "w-full flex items-center justify-between p-3 rounded-xl border transition-all duration-200",
                selectedId === region.id
                  ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-200 shadow-[0_0_15px_rgba(34,211,238,0.1)]"
                  : "bg-white/[0.02] border-white/5 text-slate-400 hover:bg-white/[0.05] hover:border-white/10"
              ].join(" ")}
            >
              <div className="flex items-center gap-3">
                <div className={[
                  "w-1.5 h-6 rounded-full",
                  selectedId === region.id ? "bg-cyan-400" : "bg-slate-700"
                ].join(" ")} />
                <div className="text-left">
                  <div className="text-xs font-bold leading-tight">{region.label}</div>
                  <div className="text-[10px] opacity-60 uppercase">{region.node_count} nodes</div>
                </div>
              </div>
              <ChevronRight size={14} className={selectedId === region.id ? "text-cyan-400" : "text-slate-600"} />
            </button>
          ))}
        </div>

        {/* Region Detail / Visualization Preview */}
        <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-4 relative overflow-hidden flex flex-col justify-center">
            {/* Visual background effect */}
            <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2 w-48 h-48 bg-cyan-500/10 blur-[80px] rounded-full pointer-events-none" />
            
            <AnimatePresence mode="wait">
              {selectedRegion ? (
                <motion.div
                  key={selectedRegion.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-4 relative z-10"
                >
                  <div>
                    <div className="text-[10px] text-cyan-500 font-bold uppercase tracking-widest mb-1">Topic Signature</div>
                    <div className="flex flex-wrap gap-2">
                       {selectedRegion.top_terms.length > 0 ? selectedRegion.top_terms.map(term => (
                         <span key={term} className="px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded-md text-[10px] text-cyan-200 flex items-center gap-1">
                           <Hash size={10} className="text-cyan-500" />
                           {term}
                         </span>
                       )) : <span className="text-[10px] text-slate-500 italic">No defining terms extracted yet</span>}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-white/[0.03] rounded-xl border border-white/5">
                      <div className="text-[10px] text-slate-500 uppercase mb-1">Density</div>
                      <div className="text-lg font-bold text-slate-100">{(selectedRegion.density * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-3 bg-white/[0.03] rounded-xl border border-white/5">
                      <div className="text-[10px] text-slate-500 uppercase mb-1">Growth</div>
                      <div className="text-lg font-bold text-emerald-400">+12%</div>
                    </div>
                  </div>

                  <div className="pt-2">
                    <button className="w-full flex items-center justify-center gap-2 py-2 bg-cyan-500 text-slate-900 rounded-lg text-xs font-bold hover:bg-cyan-400 transition-colors">
                      <Search size={14} />
                      Inspect Neural Connections
                    </button>
                  </div>
                </motion.div>
              ) : (
                <div className="text-center text-slate-500 text-xs">Select a region to browse its semantic footprint</div>
              )}
            </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
