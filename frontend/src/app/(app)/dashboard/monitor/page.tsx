"use client";

/* =============================================================================
   FAIM LAB — Monitor Page (Production - Cutting Edge Features)
   -----------------------------------------------------------------------------
   Showcases what makes FAIM UNIQUE as a memory system:
   - Memory Engine Stats (nodes, connections, evolution, growth)
   - Health History (24h)
   - Resource Usage (infrastructure)
   - Incidents, Jobs, Audit (ops)
   - Intelligence Features (batch, inference, clustering, inventing)
============================================================================= */

import React from "react";
import {
  MemoryEnginePanel,
  IncidentsPanel,
  JobsPanel,
  AuditPanel,
  ResourceUsagePanel,
  HealthHistoryChart,
  HealthCards,
  PerformanceEvolutionChart,
  RegionBrowser,
  NeuralActivityHeatmap,
  MaturityDashboard,
  IntelligenceFeaturesPanel,
  EvolutionLiveFeed,
  InventionLineage,
  CoreSettingsPanel,
  SystemHeartbeat,
  EnginePerformance,
  TopologyMapper,
} from "@/components";
import { useUserIds } from "@/contexts/UserContext";

const FALLBACK_GRAPH_ID = "U:faim-universe";

export default function MonitorPage() {
  const { graphId: userGraphId } = useUserIds();
  const graphId = userGraphId || FALLBACK_GRAPH_ID;
  const [selectedConceptId, setSelectedConceptId] = React.useState<string | null>(null);

  return (
    <div className="space-y-6">
      {/* =========================
          Header
      ========================== */}
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">
            System Monitor
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Memory engine performance, system health, and intelligence features.
          </p>
        </div>
      </header>

      {/* =========================
          Memory Engine Stats (UNIQUE)
      ========================== */}
      <section className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-950/20 to-slate-900/40 p-5">
        <MemoryEnginePanel />
      </section>

      {/* =========================
          HyperSpeed Core Transparency (NEW PHASE 4)
      ========================== */}
      <section className="grid gap-6 lg:grid-cols-2 h-[350px]">
        <EnginePerformance />
        <TopologyMapper graphId={graphId} />
      </section>

      {/* =========================
          Production Feature: Evolution & Global Heartbeat
      ========================== */}
      <section className="grid gap-6 lg:grid-cols-3 h-[450px]">
        <div className="lg:col-span-1">
           <SystemHeartbeat />
        </div>
        <div className="lg:col-span-1">
           <EvolutionLiveFeed />
        </div>
        <CoreSettingsPanel />
      </section>

      {/* =========================
          System Maturity (DIAGNOSTICS)
      ========================== */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xs font-semibold text-slate-100">System Maturity</h2>
            <p className="text-[10px] text-slate-500">Fractal Dimension, Compression, and Redundancy diagnostics.</p>
          </div>
          <div className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[9px] font-medium text-emerald-400 border border-emerald-500/20">
            Stable
          </div>
        </div>
        <MaturityDashboard />
      </section>

      {/* =========================
          Intelligence Evolution
      ========================== */}
      <section className="grid gap-6 lg:grid-cols-2">
        <PerformanceEvolutionChart />
        <RegionBrowser />
      </section>

      {/* =========================
          Growth Heatmap
      ========================== */}
      <section>
         <NeuralActivityHeatmap />
      </section>

      {/* =========================
          Health history & Status
      ========================== */}
      <section className="grid gap-6 lg:grid-cols-2">
        <HealthHistoryChart />
        <HealthCards />
      </section>

      {/* =========================
          Advanced Intelligence Features
      ========================== */}
      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
           <IntelligenceFeaturesPanel onInventionSelect={(id) => setSelectedConceptId(id)} />
        </div>
        <div className="h-[500px]">
           <InventionLineage graphId={graphId} conceptId={selectedConceptId} />
        </div>
      </section>

      {/* =========================
          Resource Usage
      ========================== */}
      <section>
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 px-1">
          Infrastructure
        </h2>
        <ResourceUsagePanel />
      </section>

      {/* =========================
          Incidents, Jobs, Audit
      ========================== */}
      <section className="grid gap-3 lg:grid-cols-3 pb-8">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
          <IncidentsPanel />
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
          <JobsPanel />
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
          <AuditPanel />
        </div>
      </section>
    </div>
  );
}
