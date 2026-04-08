"use client";

import React, { useState } from "react";
import { 
  Dna, 
  Activity, 
  HardDrive, 
  Shield, 
  Zap, 
  ArrowRight, 
  Cpu, 
  Network
} from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export default function DashboardPage() {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await new Promise((resolve) => setTimeout(resolve, 800));
    setRefreshing(false);
  };

  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader 
        title="Neural Dashboard"
        subtitle="Global resource oversight and core operational vitals"
        icon={Zap}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="success" size="md">Core Healthy</Badge>
            <Button size="sm" variant="outline" onClick={handleRefresh} loading={refreshing}>
              Refresh State
            </Button>
          </div>
        }
      />

      {/* --- Global Metric Strip --- */}
      <div
        className="grid grid-cols-1 overflow-hidden rounded-xl border sm:grid-cols-2 xl:grid-cols-4"
        style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
      >
        {[
          { label: "Active Nodes", value: "12,482", sub: "+124 today", icon: <Dna size={18} />, color: "text-cyan-200" },
          { label: "Storage Used", value: "84.2 GB", sub: "14.1% of total", icon: <HardDrive size={18} />, color: "text-emerald-400" },
          { label: "Security Keys", value: "11", sub: "4 active keys", icon: <Shield size={18} />, color: "text-amber-400" },
          { label: "Core Latency", value: "14ms", sub: "P99 responsiveness", icon: <Zap size={18} />, color: "text-rose-400" },
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
            <p className="mt-2 text-[11px] text-slate-500 uppercase tracking-widest font-bold">{stat.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:items-start">
        {/* Main Panel */}
        <div 
          className="lg:col-span-2 overflow-hidden rounded-xl border flex flex-col h-[520px]"
          style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3" style={{ borderColor: "var(--os-stroke)" }}>
            <div>
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">Active Transits</p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Real-time system event log</p>
            </div>
            <Button size="sm" variant="ghost" className="h-8 px-2 text-[10px]">View all logs</Button>
          </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {[
              { type: "INGEST", msg: "Parallel ingestion of matrix_delta_01.json completed", time: "2m ago", color: "text-emerald-400" },
              { type: "EVOLVE", msg: "Structural optimization of region U:621b... completed", time: "5m ago", color: "text-cyan-400" },
              { type: "KEY", msg: "New production API key created by admin", time: "12m ago", color: "text-amber-400" },
              { type: "SYNC", msg: "Global context synchronization in progress", time: "15m ago", color: "text-slate-400" },
              { type: "INGEST", msg: "Batch upload processed 445 vector embeddings", time: "24m ago", color: "text-emerald-400" },
              { type: "SYSTEM", msg: "Neural core version 8.2.1 successfully deployed", time: "1h ago", color: "text-rose-400" },
            ].map((log, i) => (
              <div 
                key={i} 
                className="group px-5 py-4 border-b last:border-0 transition-all hover:bg-[var(--glass-hover)]"
                style={{ borderColor: "var(--os-stroke)" }}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <span className={`text-[10px] font-black uppercase tracking-[0.2em] w-14 ${log.color}`}>{log.type}</span>
                    <p className="text-sm text-slate-100 font-medium">{log.msg}</p>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono italic shrink-0">{log.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar Panel */}
        <div 
          className="overflow-hidden rounded-xl border flex flex-col h-[520px]"
          style={{ borderColor: "var(--os-stroke)", background: "var(--os-surface-1)" }}
        >
          <div className="border-b px-5 py-1.5" style={{ borderColor: "var(--os-stroke)" }}>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">Resource Health</p>
            <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Sub-system availability matrix</p>
          </div>
          
          <div className="p-5 space-y-6">
            <div className="space-y-4">
              {[
                { label: "Core Compute", val: "24%", icon: <Cpu size={14} />, status: "success" },
                { label: "Neural Network", val: "99.9%", icon: <Network size={14} />, status: "success" },
                { label: "Storage I/O", val: "Low", icon: <Activity size={14} />, status: "warning" },
              ].map((res) => (
                <div key={res.label} className="flex items-center justify-between p-3 rounded-lg border" style={{ background: "var(--os-surface-2)", borderColor: "var(--os-stroke)" }}>
                  <div className="flex items-center gap-3">
                    <div className="text-slate-500">{res.icon}</div>
                    <span className="text-xs font-semibold text-slate-300">{res.label}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-slate-100">{res.val}</span>
                    <div className={`h-1.5 w-1.5 rounded-full ${res.status === 'success' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]' : 'bg-amber-400 animate-pulse'}`} />
                  </div>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              <p className="text-[10px] uppercase font-black tracking-widest text-slate-500">Quick Actions</p>
              <div className="grid grid-cols-1 gap-2">
                <Button variant="outline" size="sm" fullWidth className="justify-between" rightIcon={<ArrowRight size={14} />}>
                  Inspect Matrix
                </Button>
                <Button variant="outline" size="sm" fullWidth className="justify-between" rightIcon={<ArrowRight size={14} />}>
                  View Benchmarks
                </Button>
                <Button variant="outline" size="sm" fullWidth className="justify-between" rightIcon={<ArrowRight size={14} />}>
                  Export Journal
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
