"use client";

/* =============================================================================
   FAIM LAB — Monitor Page (Golden Edition)
   -----------------------------------------------------------------------------
   What Monitor is:
   - Operational cockpit: backend status, runtime telemetry, incidents/warnings.
   - This is NOT a “Dashboard duplicate”.
   - Uses SystemRuntimePanel as the core “status surface”.
============================================================================= */

import React from "react";
import SystemRuntimePanel from "@/components/SystemRuntimePanel";
import AGIFeaturesPanel from "@/components/AGIFeaturesPanel";

export default function MonitorPage() {
  return (
    <div className="space-y-4">
      {/* =========================
          Header
      ========================== */}
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">
            System Monitor
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Ops view: backend health, runtime telemetry, and warnings.
          </p>
        </div>
      </header>

      {/* =========================
          Primary ops panel
      ========================== */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <SystemRuntimePanel />
      </section>

      {/* =========================
          AGI Features Panel
      ========================== */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <AGIFeaturesPanel />
      </section>

      {/* =========================
          Placeholder blocks (safe now, wire later)
          - Incidents
          - Job queue (evolve/retention)
          - Audit log
      ========================== */}
      <section className="grid gap-3 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs font-semibold text-slate-100">Incidents</div>
          <p className="mt-2 text-[11px] text-slate-500">
            Future: list incidents (reindex failures, retention errors, backend
            restarts).
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs font-semibold text-slate-100">Jobs</div>
          <p className="mt-2 text-[11px] text-slate-500">
            Future: evolve/retention job status, last run, duration, exit code.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="text-xs font-semibold text-slate-100">Audit</div>
          <p className="mt-2 text-[11px] text-slate-500">
            Future: admin actions, user events, security/audit summaries
            (privacy-safe).
          </p>
        </div>
      </section>
    </div>
  );
}
