// /home/sephi-asi/FAIM/frontend/src/app/dashboard/page.tsx
"use client";

/* ========================================================================== */
/*  FAIM LAB — Dashboard Page (Production)                                     */
/* ========================================================================== */

import { useEffect, useState } from "react";
import { useUserIds } from "@/contexts/UserContext";
import {
  API_BASE_URL,
  fetchHealth,
  type HealthStatus,
  buildFaimHeaders,
} from "@/lib/api";

/* ========================================================================== */
/*  Types                                                                      */
/* ========================================================================== */

type UsageStats = {
  api_calls_today: number;
  api_calls_month: number;
  storage_bytes: number;
  documents_count: number;
};

/* ========================================================================== */
/*  Dashboard Page                                                             */
/* ========================================================================== */

export default function DashboardPage() {
  const { graphId } = useUserIds();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;

    async function loadData() {
      try {
        const h = await fetchHealth();
        if (alive) setHealth(h);

        // Try to load usage stats
        try {
          const res = await fetch(`${API_BASE_URL}/usage/summary`, {
            headers: buildFaimHeaders(),
          });
          if (res.ok && alive) {
            setUsage(await res.json());
          }
        } catch {
          // Usage endpoint might not exist yet
        }
      } catch (e) {
        console.warn("[dashboard] Failed to load health:", e);
      } finally {
        if (alive) setLoading(false);
      }
    }

    loadData();
    return () => { alive = false; };
  }, []);

  const isHealthy = health?.status === "ok";

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <section>
        <h1 className="text-2xl font-bold text-white mb-2">
          Welcome to FAIM Lab
        </h1>
        <p className="text-slate-400 text-sm">
          Your AI memory engine is ready. Start chatting to build your knowledge graph.
        </p>
      </section>

      {/* Status Cards */}
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          title="System Status"
          value={loading ? "Loading..." : isHealthy ? "Healthy" : "Offline"}
          status={loading ? "neutral" : isHealthy ? "ok" : "error"}
          description={health?.version ? `v${health.version}` : "Checking..."}
        />
        <StatusCard
          title="API Calls Today"
          value={usage?.api_calls_today?.toLocaleString() ?? "—"}
          status="neutral"
          description="Requests made today"
        />
        <StatusCard
          title="Storage Used"
          value={formatBytes(usage?.storage_bytes)}
          status="neutral"
          description="Total memory storage"
        />
        <StatusCard
          title="Documents"
          value={usage?.documents_count?.toLocaleString() ?? "—"}
          status="neutral"
          description="Uploaded files"
        />
      </section>

      {/* Quick Actions */}
      <section>
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Quick Actions</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <QuickActionCard
            href="/dashboard/chat"
            title="Start Chat"
            description="Ask questions and build your memory graph"
            icon="💬"
          />
          <QuickActionCard
            href="/dashboard/storage"
            title="Upload Documents"
            description="Add PDFs, text files, or images"
            icon="📄"
          />
          <QuickActionCard
            href="/dashboard/graph"
            title="View Graph"
            description="Explore your knowledge connections"
            icon="🔗"
          />
        </div>
      </section>

      {/* Getting Started */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">Getting Started</h2>
        <div className="space-y-3">
          <Step number={1} title="Start a conversation" description="Chat with FAIM to store memories and knowledge" />
          <Step number={2} title="Upload documents" description="Add PDFs, text files, or images to your memory" />
          <Step number={3} title="Ask questions" description="FAIM will recall relevant information automatically" />
        </div>
      </section>
    </div>
  );
}

/* ========================================================================== */
/*  Components                                                                 */
/* ========================================================================== */

function StatusCard({
  title,
  value,
  status,
  description,
}: {
  title: string;
  value: string;
  status: "ok" | "error" | "neutral";
  description: string;
}) {
  const statusColors = {
    ok: "border-emerald-500/30 bg-emerald-500/5",
    error: "border-rose-500/30 bg-rose-500/5",
    neutral: "border-slate-700 bg-slate-900/50",
  };

  const valueColors = {
    ok: "text-emerald-400",
    error: "text-rose-400",
    neutral: "text-white",
  };

  return (
    <div className={`rounded-xl border p-4 ${statusColors[status]}`}>
      <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">
        {title}
      </div>
      <div className={`text-xl font-semibold ${valueColors[status]}`}>
        {value}
      </div>
      <div className="text-xs text-slate-500 mt-1">{description}</div>
    </div>
  );
}

function QuickActionCard({
  href,
  title,
  description,
  icon,
}: {
  href: string;
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <a
      href={href}
      className="group rounded-xl border border-slate-700 bg-slate-900/50 p-4 transition-all hover:border-cyan-500/50 hover:bg-slate-800/50"
    >
      <div className="text-2xl mb-2">{icon}</div>
      <div className="text-sm font-medium text-white group-hover:text-cyan-400 transition-colors">
        {title}
      </div>
      <div className="text-xs text-slate-400 mt-1">{description}</div>
    </a>
  );
}

function Step({
  number,
  title,
  description,
}: {
  number: number;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-bold flex items-center justify-center">
        {number}
      </div>
      <div>
        <div className="text-sm font-medium text-white">{title}</div>
        <div className="text-xs text-slate-400">{description}</div>
      </div>
    </div>
  );
}

/* ========================================================================== */
/*  Helpers                                                                    */
/* ========================================================================== */

function formatBytes(bytes?: number | null): string {
  const n = typeof bytes === "number" && Number.isFinite(bytes) ? bytes : 0;
  if (n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let idx = 0;
  let value = n;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${units[idx]}`;
}
