"use client";

import React from "react";
import { 
  Activity, 
  Cpu, 
  Network, 
  Database, 
  Zap, 
  ArrowRight,
  Maximize2
} from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export default function MonitorPage() {
  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />
      
      <GlassHeader
        title="Core Vitals"
        subtitle="Real-time Neural Core Vitals and System Throughput"
        icon={Activity}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="success" size="md">Real-time</Badge>
            <Button size="sm" variant="outline">Telemetry Repo</Button>
          </div>
        }
      />

      {/* --- Monitor Metric Strip --- */}
      <div
        className="grid grid-cols-1 overflow-hidden rounded-xl border sm:grid-cols-2 xl:grid-cols-4"
        style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
      >
        {[
          { label: "Core Compute", value: "24.8%", sub: "8 logic units", icon: <Cpu size={18} />, color: "text-cyan-200" },
          { label: "Memory Load", value: "12.2 GB", sub: "of 32GB total", icon: <Database size={18} />, color: "text-emerald-400" },
          { label: "Network I/O", value: "840 Mbps", sub: "Transit active", icon: <Network size={18} />, color: "text-amber-400" },
          { label: "System Uptime", value: "14d 2h", sub: "Since v8.2 patch", icon: <Zap size={18} />, color: "text-rose-400" },
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
        {/* Telemetry Stream Panel */}
        <div 
          className="lg:col-span-3 overflow-hidden rounded-xl border flex flex-col h-[550px]"
          style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3" style={{ borderColor: "var(--os-stroke)" }}>
            <div>
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">Telemetry Stream</p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Low-latency pulse monitor</p>
            </div>
            <div className="flex items-center gap-1">
               <div className="h-1.5 w-8 rounded-full bg-emerald-400/20" />
               <div className="h-1.5 w-12 rounded-full bg-emerald-400/40" />
               <div className="h-1.5 w-6 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
            </div>
          </div>
          
          <div className="flex-1 p-6 space-y-6 overflow-y-auto custom-scrollbar">
            {[
              { component: "Logic Engine", load: 24, status: "stable", traffic: "1.2k ops" },
              { component: "Vector Core", load: 68, status: "peak", traffic: "8.4k ops" },
              { component: "Recall Matrix", load: 12, status: "idle", traffic: "0.2k ops" },
              { component: "Pruning Handler", load: 4, status: "standby", traffic: "0.0k ops" },
            ].map((comp) => (
              <div key={comp.component} className="space-y-3 p-4 rounded-xl border" style={{ background: "var(--os-surface-2)", borderColor: "var(--os-stroke)" }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`h-2 w-2 rounded-full ${comp.status === 'peak' ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
                    <span className="text-xs font-bold text-slate-100 uppercase tracking-widest">{comp.component}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">{comp.traffic}</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex-1 h-1.5 bg-black/40 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-cyan-400 transition-all duration-1000" 
                      style={{ width: `${comp.load}%`, boxShadow: "0 0 10px rgba(34,211,238,0.4)" }}
                    />
                  </div>
                  <span className="text-xs font-mono text-cyan-400 w-10 text-right">{comp.load}%</span>
                </div>
              </div>
            ))}
            
            <div className="pt-4 p-4 rounded-xl border border-dashed border-slate-800 flex flex-col items-center justify-center min-h-[140px] text-center opacity-40 hover:opacity-100 transition-opacity group">
               <Maximize2 className="text-slate-500 mb-2 group-hover:scale-110 transition-transform" size={24} />
               <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Expand Visual Topology</p>
            </div>
          </div>
        </div>

        {/* Global Distribution Sidebar */}
        <div 
          className="lg:col-span-2 overflow-hidden rounded-xl border flex flex-col h-[550px]"
          style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
        >
          <div className="border-b px-5 py-1.5" style={{ borderColor: "var(--os-stroke)" }}>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">Node Distribution</p>
            <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Geometric cluster density</p>
          </div>
          
          <div className="p-6 space-y-8">
            <div className="relative aspect-square rounded-full border border-dashed border-slate-800 flex items-center justify-center">
               <div className="absolute inset-4 rounded-full border border-dashed border-slate-800 opacity-60" />
               <div className="absolute inset-12 rounded-full border border-dashed border-slate-800 opacity-40" />
               <div className="absolute inset-20 rounded-full border border-dashed border-slate-800 opacity-20" />
               
               {/* "Nodes" */}
               <div className="absolute top-1/4 left-1/4 h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.8)]" />
               <div className="absolute bottom-1/3 right-1/4 h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]" />
               <div className="absolute top-1/2 right-1/3 h-2 w-2 rounded-full bg-amber-400 shadow-[0_0_12px_rgba(251,191,36,0.8)]" />
               
               <div className="text-center">
                  <p className="text-2xl font-black text-white">42%</p>
                  <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Global Density</p>
               </div>
            </div>

            <div className="space-y-3 pt-4">
              <Button fullWidth variant="outline" size="sm" className="justify-between" rightIcon={<ArrowRight size={14} />}>
                Deep Pulse Analysis
              </Button>
              <Button fullWidth variant="outline" size="sm" className="justify-between" rightIcon={<ArrowRight size={14} />}>
                Export Sensor Data
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
