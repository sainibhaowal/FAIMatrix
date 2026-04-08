"use client";

import React from "react";
import { 
  BarChart3, 
  Zap, 
  Activity, 
  Target, 
  Gauge, 
  ArrowUpRight,
  Database
} from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export default function BenchmarksPage() {
  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader 
        title="Engine Maturity"
        subtitle="Standardized Model Performance and Latency Matrix"
        icon={BarChart3}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="outline" size="md" className="border-cyan-500/30 text-cyan-400 bg-cyan-500/5">
              Protocol v8.4
            </Badge>
            <Button size="sm" variant="outline">Run Benchmark</Button>
          </div>
        }
      />

      {/* --- Benchmarks Metric Strip --- */}
      <div
        className="grid grid-cols-1 overflow-hidden rounded-xl border sm:grid-cols-2 xl:grid-cols-4"
        style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
      >
        {[
          { label: "Maturity Score", value: "94.2", sub: "Top 5% of graphs", icon: <Target size={18} />, color: "text-emerald-400" },
          { label: "Avg Latency", value: "242ms", sub: "-14ms since update", icon: <Zap size={18} />, color: "text-cyan-200" },
          { label: "Throughput", value: "1.2k", sub: "req / second", icon: <Activity size={18} />, color: "text-amber-400" },
          { label: "Core Stability", value: "99.98%", sub: "Zero-fault tolerance", icon: <Gauge size={18} />, color: "text-rose-400" },
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
            <p className="mt-2 text-[10px] text-slate-500 font-bold uppercase tracking-widest">{stat.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5 lg:items-start">
        {/* Performance Matrix Panel */}
        <div 
          className="lg:col-span-3 overflow-hidden rounded-xl border flex flex-col"
          style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
        >
          <div className="flex items-center justify-between border-b px-5 py-3" style={{ borderColor: "var(--os-stroke)" }}>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">Model Performance Matrix</p>
            <div className="flex gap-1">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-400/50" />
              <div className="h-1.5 w-1.5 rounded-full bg-slate-400/20" />
              <div className="h-1.5 w-1.5 rounded-full bg-slate-400/20" />
            </div>
          </div>
          
          <div className="p-6 space-y-8">
            {[
              { model: "gemini-1.5-pro", latency: 85, maturity: 98, traffic: "4.2k ops" },
              { model: "claude-3-sonnet", latency: 62, maturity: 92, traffic: "2.1k ops" },
              { model: "gpt-4o-mini", latency: 45, maturity: 88, traffic: "1.8k ops" },
              { model: "gpt-4-turbo", latency: 92, maturity: 96, traffic: "1.1k ops" },
            ].map((perf) => (
              <div key={perf.model} className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-200 font-mono">{perf.model}</span>
                    <Badge variant="outline" size="xs" className="text-[9px] h-4 py-0 opacity-50">{perf.traffic}</Badge>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">{perf.latency}ms latency</span>
                </div>
                <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-emerald-400/60 rounded-full transition-all duration-1000" 
                    style={{ width: `${perf.maturity}%`, boxShadow: "0 0 10px rgba(52,211,153,0.3)" }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Diagnostic Panel */}
        <div 
          className="lg:col-span-2 space-y-4"
        >
          <div 
            className="overflow-hidden rounded-xl border flex flex-col"
            style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
          >
            <div className="border-b px-5 py-1.5" style={{ borderColor: "var(--os-stroke)" }}>
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">Maturity Diagnostic</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-start gap-4 p-4 rounded-lg" style={{ background: "rgba(99,102,241,0.05)", border: "1px solid rgba(99,102,241,0.1)" }}>
                <Database size={16} className="text-indigo-400 mt-0.5" />
                <div>
                  <p className="text-xs font-bold text-indigo-200 uppercase tracking-widest mb-1">Structural Health</p>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Graph evolution shows 14% novelty increase in the last 24h. Structural entropy remains below established critical thresholds.
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3 pt-2">
                {[
                  { label: "Stability", val: "High" },
                  { label: "Recall", val: "99.2%" },
                  { label: "Precision", val: "98.7%" },
                  { label: "Density", val: "0.24" },
                ].map((stat) => (
                  <div key={stat.label} className="p-3 rounded-lg border text-center" style={{ background: "var(--os-surface-2)", borderColor: "var(--os-stroke)" }}>
                    <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">{stat.label}</p>
                    <p className="text-sm font-bold text-slate-200">{stat.val}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="border-t px-5 py-3 bg-black/20" style={{ borderColor: "var(--os-stroke)" }}>
              <Button fullWidth variant="ghost" size="sm" className="text-[10px] justify-between uppercase tracking-widest" rightIcon={<ArrowUpRight size={14} />}>
                Detailed Telemetry Repo
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
