"use client";

import React, { useState, useEffect } from "react";
import { Settings2, Save, RotateCcw, Sliders, Target, Gauge, Zap } from "lucide-react";

interface EvolutionConfig {
  lambda_h: number;
  max_region_size: number;
  merge_similarity_threshold: number;
  redundancy_similarity_threshold: number;
  prune_min_use_count: number;
  promote_min_use_count: number;
}

export default function CoreSettingsPanel() {
  const [config, setConfig] = useState<EvolutionConfig | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchConfig = async () => {
    try {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers: Record<string, string> = {};
      if (session && (session as any).accessToken) {
        headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const res = await fetch("/api/ops/evolution/config", { headers });
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (err) {
      console.error("Failed to fetch evolution config:", err);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setIsSaving(true);
    setMessage(null);
    try {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (session && (session as any).accessToken) {
        headers["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const res = await fetch("/api/ops/evolution/config", {
        method: "PATCH",
        headers,
        body: JSON.stringify(config),
      });
      if (res.ok) {
        setMessage({ type: "success", text: "System parameters updated successfully" });
        setTimeout(() => setMessage(null), 3000);
      } else {
        setMessage({ type: "error", text: "Failed to update parameters" });
      }
    } catch (err) {
      setMessage({ type: "error", text: "Network error while saving" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (confirm("Reset all parameters to factory defaults?")) {
      // Logic would go here, for now just refetch
      fetchConfig();
    }
  };

  if (!config) return null;

  return (
    <div className="flex flex-col h-full bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/60 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Settings2 className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-tight">
            Core Evolution Controls
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={handleReset}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-500 transition-colors"
            title="Reset to defaults"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
          <button 
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition-all shadow-lg shadow-violet-900/20"
          >
            {isSaving ? (
              <div className="h-3 w-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            SAVE
          </button>
        </div>
      </div>

      {/* Settings Grid */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {message && (
          <div className={`p-2.5 rounded-lg border text-xs font-medium animate-in fade-in slide-in-from-top-2 ${
            message.type === "success" 
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" 
              : "bg-rose-500/10 border-rose-500/20 text-rose-400"
          }`}>
            {message.text}
          </div>
        )}

        {/* Objective Tuning */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-slate-300 font-bold">
            <Sliders className="h-3.5 w-3.5 text-violet-400" />
            <span className="text-[10px] uppercase tracking-widest">Objective Tuning (P1)</span>
          </div>
          
          <div className="space-y-1.5">
            <div className="flex justify-between items-center px-1">
              <label className="text-xs text-slate-400">Entropy Weight (λ)</label>
              <span className="text-xs font-mono text-violet-400">{config.lambda_h.toFixed(2)}</span>
            </div>
            <input 
              type="range" min="0" max="1" step="0.05"
              value={config.lambda_h}
              onChange={(e) => setConfig({...config, lambda_h: parseFloat(e.target.value)})}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-violet-500"
            />
            <div className="flex justify-between text-[9px] text-slate-600 font-mono px-0.5">
              <span>EXPLORATIVE (D)</span>
              <span>STABLE (H)</span>
            </div>
          </div>
        </div>

        {/* Thresholds */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center gap-2 text-slate-300 font-bold">
            <Target className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-[10px] uppercase tracking-widest">Decision Thresholds</span>
          </div>

          <div className="grid grid-cols-1 gap-4">
            <div className="space-y-1.5">
              <div className="flex justify-between items-center px-1">
                <label className="text-xs text-slate-400">Merge Similarity</label>
                <span className="text-xs font-mono text-emerald-400">{config.merge_similarity_threshold.toFixed(2)}</span>
              </div>
              <input 
                type="range" min="0.80" max="1.0" step="0.01"
                value={config.merge_similarity_threshold}
                onChange={(e) => setConfig({...config, merge_similarity_threshold: parseFloat(e.target.value)})}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
            </div>

            <div className="space-y-1.5 pt-2">
               <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                     <div className="p-1 rounded bg-slate-800">
                        <Gauge className="h-3 w-3 text-slate-500" />
                     </div>
                     <span className="text-xs text-slate-400 text-slate-400">Region Size Cap</span>
                  </div>
                  <input 
                    type="number"
                    value={config.max_region_size}
                    onChange={(e) => setConfig({...config, max_region_size: parseInt(e.target.value)})}
                    className="w-16 bg-slate-950 border border-slate-800 rounded px-1.5 py-0.5 text-xs text-slate-300 font-mono focus:border-violet-500/50 outline-none"
                  />
               </div>
            </div>

            <div className="space-y-1.5">
               <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                     <div className="p-1 rounded bg-slate-800">
                        <Zap className="h-3 w-3 text-amber-500" />
                     </div>
                     <span className="text-xs text-slate-400">Promotion Usage Min</span>
                  </div>
                  <input 
                    type="number"
                    value={config.promote_min_use_count}
                    onChange={(e) => setConfig({...config, promote_min_use_count: parseInt(e.target.value)})}
                    className="w-16 bg-slate-950 border border-slate-800 rounded px-1.5 py-0.5 text-xs text-slate-300 font-mono focus:border-violet-500/50 outline-none"
                  />
               </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="px-4 py-2 bg-slate-950/40 border-t border-slate-800/50 text-[10px] text-slate-600 italic">
        Caution: Changes here affect background autonomic graph restructuring in real-time.
      </div>
    </div>
  );
}
