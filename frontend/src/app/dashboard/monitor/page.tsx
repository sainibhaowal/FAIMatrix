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
import { MemoryEnginePanel } from "@/components/monitor/MemoryEnginePanel";
import AGIFeaturesPanel from "@/components/AGIFeaturesPanel";
import { IncidentsPanel } from "@/components/monitor/IncidentsPanel";
import { JobsPanel } from "@/components/monitor/JobsPanel";
import { AuditPanel } from "@/components/monitor/AuditPanel";
import { ResourceUsagePanel } from "@/components/monitor/ResourceUsagePanel";
import { HealthHistoryChart } from "@/components/monitor/HealthHistoryChart";
import { HealthCards } from "@/components/monitor/HealthCards";

export default function MonitorPage() {
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
          Health History Chart
      ========================== */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <HealthHistoryChart />
      </section>

      {/* =========================
          System Health Status
      ========================== */}
      <section>
        <HealthCards />
      </section>

      {/* =========================
          Resource Usage
      ========================== */}
      <section>
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Infrastructure
        </h2>
        <ResourceUsagePanel />
      </section>

      {/* =========================
          Incidents, Jobs, Audit
      ========================== */}
      <section className="grid gap-3 lg:grid-cols-3">
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

      {/* =========================
          Intelligence Features
      ========================== */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <AGIFeaturesPanel />
      </section>
    </div>
  );
}
