"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Activity,
  ArrowRight,
  Brain,
  Dna,
  HardDrive,
  KeyRound,
  Layers,
  Network,
  PlayCircle,
  RefreshCw,
  Shield,
  ShieldCheck,
  Sparkles,
  Upload,
  Zap,
} from "lucide-react";
import { getSession } from "next-auth/react";
import { useRouter } from "next/navigation";

import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useUser } from "@/contexts/UserContext";
import { readJsonSafely } from "@/lib/safeFetch";

// ─── Auth helper ──────────────────────────────────────────────────────────────

async function authHeaders(): Promise<Record<string, string>> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScorecardData {
  node_count: number;
  edge_count: number;
  density: number;
  entropy: number;
  spectral_radius: number;
  graph_version?: number;
}

interface StorageSummary {
  total_bytes: number;
  total_files: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
}

interface EvolveStatusJob {
  job_id: string;
  status: string;
  created_at?: string | null;
  completed_at?: string | null;
}

interface EvolveStatusResponse {
  graph_id: string;
  runtime: { is_running: boolean; worker_count?: number };
  due: { is_due: boolean; version_delta: number };
  active_job?: EvolveStatusJob | null;
  last_enqueued_job?: EvolveStatusJob | null;
  last_event: {
    last_event_seq: number;
    last_event_kind?: string | null;
    last_event_ts?: string | null;
  };
}

interface ApiKeyListResponse {
  total: number;
  items: { is_active: boolean }[];
}

interface FaimEvent {
  seq: number;
  id: string;
  kind: string;
  ts: string | null;
  payload: Record<string, unknown>;
}

interface LatestInfo {
  last_seq: number;
  event_count: number;
  last_kind: string | null;
  last_ts: string | null;
}

interface HealthData {
  status: string;
  latency_ms?: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function relTime(ts: string | null | undefined): string {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const EVENT_KIND_META: Record<string, { label: string; color: string }> = {
  NODE_UPSERT: { label: "UPSERT", color: "text-cyan-400" },
  INVENT_MACRO_NODE: { label: "MACRO", color: "text-violet-400" },
  PRUNE_NODE: { label: "PRUNE", color: "text-rose-400" },
  MERGE: { label: "MERGE", color: "text-blue-400" },
  EVOLUTION_MERGE: { label: "EVOLVE", color: "text-emerald-400" },
  EVOLUTION_COMPLETE: { label: "EVOLVED", color: "text-emerald-300" },
  EVOLUTION_SKIPPED: { label: "SKIP", color: "text-slate-500" },
  GRAPH_VERSION_BUMP: { label: "VERSION", color: "text-amber-400" },
  INHERITANCE_SET: { label: "INHERIT", color: "text-cyan-300" },
  DIAGNOSTICS_SNAPSHOT: { label: "DIAG", color: "text-slate-400" },
  QUERY_START: { label: "QUERY", color: "text-amber-300" },
  QUERY_RERANKED: { label: "RANK", color: "text-amber-400" },
  QUERY_TOUCH: { label: "TOUCH", color: "text-slate-400" },
  QUERY_COMPLETE: { label: "DONE", color: "text-emerald-400" },
  STORAGE_RAW_STORED: { label: "STORE", color: "text-blue-400" },
  STORAGE_ENCRYPT_FAILED: { label: "ERR", color: "text-rose-500" },
};

function eventMeta(kind: string) {
  return (
    EVENT_KIND_META[kind] ?? {
      label: kind.slice(0, 7).toUpperCase(),
      color: "text-slate-400",
    }
  );
}

function eventSummary(ev: FaimEvent): string {
  const p = ev.payload;
  switch (ev.kind) {
    case "NODE_UPSERT":
      return `Node upserted: ${String(p.node_id ?? p.id ?? "").slice(0, 16)}`;
    case "INVENT_MACRO_NODE":
      return `Macro node invented: ${String(p.label ?? p.node_id ?? "").slice(0, 30)}`;
    case "PRUNE_NODE":
      return `Node pruned: ${String(p.node_id ?? "").slice(0, 20)}`;
    case "EVOLUTION_COMPLETE":
      return `Evolution complete — ${p.nodes_processed ?? ""} nodes processed`;
    case "EVOLUTION_SKIPPED":
      return "Evolution skipped — graph unchanged";
    case "GRAPH_VERSION_BUMP":
      return `Graph version → ${p.version ?? ""}`;
    case "QUERY_START":
      return `Query started: "${String(p.query ?? "").slice(0, 40)}"`;
    case "QUERY_COMPLETE":
      return `Query complete — ${p.result_count ?? ""} results`;
    case "STORAGE_RAW_STORED":
      return `Stored ${String(p.filename ?? p.file_id ?? "").slice(0, 30)}`;
    case "MERGE":
    case "EVOLUTION_MERGE":
      return `Edge merge: ${String(p.source ?? "").slice(0, 10)} → ${String(p.target ?? "").slice(0, 10)}`;
    default:
      return `${ev.kind} event`;
  }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function KpiCell({
  icon,
  label,
  value,
  sub,
  color,
  loading,
  className,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  color: string;
  loading?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`relative flex flex-col justify-center px-4 sm:px-6 py-4 border-slate-800/50 ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
          {label}
        </p>
        <div className="opacity-20">{icon}</div>
      </div>
      {loading ? (
        <div className="h-7 w-24 rounded animate-pulse bg-slate-700/40 mb-2" />
      ) : (
        <p
          className={`font-semibold tabular-nums leading-none text-[26px] ${color}`}
        >
          {value}
        </p>
      )}
      <p className="mt-2 text-[11px] text-slate-500 uppercase tracking-widest font-bold">
        {sub}
      </p>
    </div>
  );
}

function PanelHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3 shrink-0"
      style={{ borderColor: "var(--os-stroke)" }}
    >
      <div>
        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
          {title}
        </p>
        {subtitle && (
          <p className="text-[10px] text-slate-500 mt-0.5">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}

function ScorecardGauge({
  label,
  value,
  hint,
  color,
}: {
  label: string;
  value: number;
  hint: string;
  color: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-0.5 py-3 px-2 sm:px-4 rounded-xl border text-center"
      style={{
        background: "var(--os-surface-2)",
        borderColor: "var(--os-stroke)",
      }}
    >
      <span
        className="font-mono text-[16px] sm:text-[18px] font-bold"
        style={{ color }}
      >
        {value > 0 ? value.toFixed(2) : "0"}
      </span>
      <span className="text-[8px] sm:text-[9px] uppercase tracking-widest text-slate-500">
        {label}
      </span>
      <span
        className="text-[7px] sm:text-[8px] font-mono"
        style={{ color, opacity: 0.7 }}
      >
        {hint}
      </span>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const { graphId } = useUser();

  // ── State ──
  const [scorecard, setScorecard] = useState<ScorecardData | null>(null);
  const [storage, setStorage] = useState<StorageSummary | null>(null);
  const [evolveStatus, setEvolveStatus] = useState<EvolveStatusResponse | null>(
    null,
  );
  const [keyCount, setKeyCount] = useState<{
    total: number;
    active: number;
  } | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [events, setEvents] = useState<FaimEvent[]>([]);
  const [latestInfo, setLatestInfo] = useState<LatestInfo | null>(null);

  const [scorecardLoading, setScorecardLoading] = useState(true);
  const [storageLoading, setStorageLoading] = useState(true);
  const [evolveLoading, setEvolveLoading] = useState(true);
  const [keysLoading, setKeysLoading] = useState(true);
  const [eventsLoading, setEventsLoading] = useState(true);
  const [evolving, setEvolving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch fns ──

  const fetchScorecard = useCallback(async () => {
    if (!graphId) return;
    try {
      const headers = await authHeaders();
      const res = await fetch(`/api/v1/metrics/scorecard?graph_id=${graphId}`, {
        headers,
      });
      if (!res.ok) return;
      const data = await readJsonSafely<any>(res);
      if (!data) return;
      setScorecard(data);
    } catch {
      // silent
    } finally {
      setScorecardLoading(false);
    }
  }, [graphId]);

  const fetchStorage = useCallback(async () => {
    if (!graphId) return;
    try {
      const headers = await authHeaders();
      const res = await fetch(`/api/v1/storage/summary?graph_id=${graphId}`, {
        headers,
      });
      if (!res.ok) return;
      const data = await readJsonSafely<any>(res);
      if (!data) return;
      setStorage(data);
    } catch {
      // silent
    } finally {
      setStorageLoading(false);
    }
  }, [graphId]);

  const fetchEvolveStatus = useCallback(async () => {
    if (!graphId) return;
    try {
      const headers = await authHeaders();
      const res = await fetch(`/api/v1/evolve/status?graph_id=${graphId}`, {
        headers,
      });
      if (!res.ok) return;
      const data = await readJsonSafely<any>(res);
      if (!data) return;
      setEvolveStatus(data);
    } catch {
      // silent
    } finally {
      setEvolveLoading(false);
    }
  }, [graphId]);

  const fetchKeys = useCallback(async () => {
    try {
      const headers = await authHeaders();
      const res = await fetch("/api/v1/api-keys", { headers });
      if (!res.ok) return;
      const data = await readJsonSafely<ApiKeyListResponse>(res);
      if (!data) return;
      const active = data.items.filter((k) => k.is_active).length;
      setKeyCount({ total: data.total, active });
    } catch {
      // silent
    } finally {
      setKeysLoading(false);
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) return;
      const data = await readJsonSafely<any>(res);
      if (!data) return;
      setHealth(data);
    } catch {
      // silent
    }
  }, []);

  const fetchEvents = useCallback(
    async (since?: number) => {
      if (!graphId) return;
      try {
        const headers = await authHeaders();
        const latestRes = await fetch(
          `/api/v1/events/latest?graph_id=${graphId}`,
          { headers },
        );
        if (!latestRes.ok) return;
        const latest = await readJsonSafely<LatestInfo>(latestRes);
        if (!latest) return;
        setLatestInfo(latest);

        const afterSeq = since ?? Math.max(0, latest.last_seq - 30);
        const res = await fetch(
          `/api/v1/events?graph_id=${graphId}&after_seq=${afterSeq}&limit=30`,
          { headers },
        );
        if (!res.ok) return;
        const data = await readJsonSafely<{ events?: FaimEvent[] }>(res);
        if (!data) return;
        const fetched: FaimEvent[] = data.events ?? [];

        setEvents((prev) => {
          if (since === undefined) {
            return fetched.sort((a, b) => b.seq - a.seq);
          }
          const ids = new Set(prev.map((e) => e.id));
          const newOnes = fetched.filter((e) => !ids.has(e.id));
          if (!newOnes.length) return prev;
          return [...newOnes, ...prev]
            .slice(0, 50)
            .sort((a, b) => b.seq - a.seq);
        });
      } catch {
        // silent
      } finally {
        setEventsLoading(false);
      }
    },
    [graphId],
  );

  // ── Initial load ──

  useEffect(() => {
    if (!graphId) return;
    fetchScorecard();
    fetchStorage();
    fetchEvolveStatus();
    fetchKeys();
    fetchHealth();
    fetchEvents();
  }, [
    graphId,
    fetchScorecard,
    fetchStorage,
    fetchEvolveStatus,
    fetchKeys,
    fetchHealth,
    fetchEvents,
  ]);

  // ── Polling: events every 10s, scorecard+evolve every 30s ──

  const lastSeqRef = useRef<number>(0);
  useEffect(() => {
    if (latestInfo) lastSeqRef.current = latestInfo.last_seq;
  }, [latestInfo]);

  useEffect(() => {
    if (!graphId) return;
    const evtInterval = setInterval(() => {
      fetchEvents(lastSeqRef.current);
    }, 10_000);
    const slowInterval = setInterval(() => {
      fetchScorecard();
      fetchEvolveStatus();
      fetchStorage();
    }, 30_000);
    return () => {
      clearInterval(evtInterval);
      clearInterval(slowInterval);
    };
  }, [graphId, fetchEvents, fetchScorecard, fetchEvolveStatus, fetchStorage]);

  // ── Evolve action ──

  const runEvolve = useCallback(async () => {
    if (!graphId || evolving) return;
    setEvolving(true);
    try {
      const headers = await authHeaders();
      await fetch(`/api/v1/evolve`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ graph_id: graphId, profile: "strict" }),
      });
      setTimeout(() => {
        fetchEvolveStatus();
        fetchScorecard();
        fetchEvents(lastSeqRef.current);
      }, 2000);
    } catch {
      // silent
    } finally {
      setTimeout(() => setEvolving(false), 3000);
    }
  }, [graphId, evolving, fetchEvolveStatus, fetchScorecard, fetchEvents]);

  // ── Upload action ──

  const handleFileUpload = useCallback(
    async (file: File) => {
      if (!graphId || uploading) return;
      setUploading(true);
      try {
        const headers = await authHeaders();
        const form = new FormData();
        form.append("file", file);
        form.append("graph_id", graphId);
        await fetch(`/api/v1/storage/uploads`, {
          method: "POST",
          headers,
          body: form,
        });
        setTimeout(() => {
          fetchStorage();
          fetchEvents(lastSeqRef.current);
        }, 1500);
      } catch {
        // silent
      } finally {
        setTimeout(() => setUploading(false), 2000);
      }
    },
    [graphId, uploading, fetchStorage, fetchEvents],
  );

  // ── Derived values ──

  const healthOk = health?.status === "ok" || health?.status === "healthy";

  const scorecardGauges = useMemo(() => {
    const d = scorecard?.density ?? 0;
    const h = scorecard?.entropy ?? 0;
    const l = scorecard?.spectral_radius ?? 0;
    return [
      {
        label: "D — Density",
        value: d,
        hint: d >= 0.15 ? "dense" : d >= 0.05 ? "sparse" : "disconnected",
        color: d >= 0.15 ? "#22d3ee" : d >= 0.05 ? "#fbbf24" : "#64748b",
      },
      {
        label: "H — Entropy",
        value: h,
        hint: h >= 0.8 ? "diverse" : h >= 0.3 ? "moderate" : "uniform",
        color: h >= 0.8 ? "#a78bfa" : h >= 0.3 ? "#fbbf24" : "#64748b",
      },
      {
        label: "λ — Spectral",
        value: l,
        hint: l >= 2.0 ? "clustered" : l >= 0.5 ? "moderate" : "sparse",
        color: l >= 2.0 ? "#34d399" : l >= 0.5 ? "#fbbf24" : "#64748b",
      },
    ];
  }, [scorecard]);

  const evolveJobStatus =
    evolveStatus?.active_job?.status ??
    evolveStatus?.last_enqueued_job?.status ??
    "idle";
  const evolveIsRunning = evolveStatus?.runtime?.is_running ?? false;
  const evolveLastRun =
    evolveStatus?.last_enqueued_job?.completed_at ??
    evolveStatus?.last_enqueued_job?.created_at ??
    null;
  const evolveHealthColor = evolveIsRunning
    ? "text-cyan-400"
    : evolveJobStatus === "completed"
      ? "text-emerald-400"
      : evolveJobStatus === "error" || evolveJobStatus === "failed"
        ? "text-rose-400"
        : "text-slate-400";

  const QUICK_ACTIONS = [
    {
      label: "Open FIG View",
      icon: <Network size={14} />,
      href: "/dashboard/fig-view",
    },
    {
      label: "Memory Query",
      icon: <Brain size={14} />,
      href: "/dashboard/memory-query",
    },
    {
      label: "View Journal",
      icon: <Activity size={14} />,
      href: "/dashboard/journal",
    },
    {
      label: "API Keys",
      icon: <KeyRound size={14} />,
      href: "/dashboard/api-keys",
    },
    {
      label: "Storage",
      icon: <HardDrive size={14} />,
      href: "/dashboard/storage",
    },
  ];

  return (
    <div className="relative flex flex-col gap-4 pb-8 px-1 text-slate-100">
      <div className="faim-grid" />

      <GlassHeader
        title="Command Center"
        subtitle="Live graph health, activity feed, and operational controls"
        icon={Zap}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant={healthOk ? "success" : "warning"} size="md">
              {healthOk ? "System Online" : "Checking…"}
            </Badge>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                fetchScorecard();
                fetchStorage();
                fetchEvolveStatus();
                fetchKeys();
                fetchHealth();
                fetchEvents();
              }}
            >
              <RefreshCw size={13} className="mr-1.5" />
              Refresh
            </Button>
          </div>
        }
      />

      {/* ── Row 1 — KPI Strip ────────────────────────────────────────────── */}
      <div
        className="grid grid-cols-2 xl:grid-cols-4 overflow-hidden rounded-xl border"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        <KpiCell
          icon={<Dna size={18} />}
          label="Active Nodes"
          value={
            scorecardLoading
              ? "…"
              : (scorecard?.node_count ?? 0).toLocaleString()
          }
          sub={`${scorecard?.edge_count?.toLocaleString() ?? "—"} edges`}
          color="text-cyan-300"
          loading={scorecardLoading}
        />
        <KpiCell
          icon={<HardDrive size={18} />}
          label="Storage Used"
          value={storageLoading ? "…" : fmtBytes(storage?.total_bytes ?? 0)}
          sub={`${storage?.total_files ?? "—"} files`}
          color="text-emerald-400"
          loading={storageLoading}
          className="border-l"
        />
        <KpiCell
          icon={<Shield size={18} />}
          label="API Keys"
          value={keysLoading ? "…" : String(keyCount?.total ?? 0)}
          sub={`${keyCount?.active ?? "—"} active`}
          color="text-amber-400"
          loading={keysLoading}
          className="border-t xl:border-t-0 xl:border-l"
        />
        <KpiCell
          icon={<Zap size={18} />}
          label="System Health"
          value={health ? (healthOk ? "Online" : "Error") : "…"}
          sub={
            health?.latency_ms != null
              ? `${health.latency_ms}ms latency`
              : "checking…"
          }
          color={healthOk ? "text-emerald-400" : "text-rose-400"}
          className="border-t xl:border-t-0 border-l"
        />
      </div>

      {/* ── Row 2 — Main Grid ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
        {/* Activity Feed — 2 cols */}
        <div
          className="lg:col-span-2 flex flex-col rounded-xl border overflow-hidden"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
            height: "420px",
          }}
        >
          <PanelHeader
            title="Live Activity"
            subtitle="Real-time graph events — auto-updating every 10s"
            action={
              latestInfo && (
                <span className="text-[10px] font-mono text-slate-500">
                  seq #{latestInfo.last_seq} · {latestInfo.event_count} total
                </span>
              )
            }
          />
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {eventsLoading ? (
              <div className="flex flex-col gap-0">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="px-5 py-4 border-b"
                    style={{ borderColor: "var(--os-stroke)" }}
                  >
                    <div className="h-4 w-3/4 rounded animate-pulse bg-slate-700/40" />
                  </div>
                ))}
              </div>
            ) : events.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
                <Activity size={28} className="opacity-30" />
                <p className="text-sm">
                  No events yet — ingest data to see activity
                </p>
              </div>
            ) : (
              events.map((ev) => {
                const meta = eventMeta(ev.kind);
                return (
                  <div
                    key={ev.id}
                    className="group px-5 py-3 border-b last:border-0 transition-all hover:bg-slate-800/30"
                    style={{ borderColor: "var(--os-stroke)" }}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-4 min-w-0">
                        <span
                          className={`text-[10px] font-black uppercase tracking-[0.12em] w-14 shrink-0 ${meta.color}`}
                        >
                          {meta.label}
                        </span>
                        <p className="text-sm text-slate-200 font-medium truncate">
                          {eventSummary(ev)}
                        </p>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono shrink-0">
                        {relTime(ev.ts)}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right column: Graph Health + Quick Actions */}
        <div className="flex flex-col gap-4">
          {/* Graph Health */}
          <div
            className="rounded-xl border overflow-hidden"
            style={{
              borderColor: "var(--os-stroke)",
              background: "var(--os-surface-1)",
            }}
          >
            <PanelHeader
              title="Graph Health"
              subtitle="Topology scorecard — D / H / λ"
              action={
                scorecard?.graph_version != null && (
                  <span className="text-[10px] font-mono text-slate-500">
                    v{scorecard.graph_version}
                  </span>
                )
              }
            />
            <div className="p-4 space-y-4">
              {scorecardLoading ? (
                <div className="grid grid-cols-3 gap-2">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="h-16 rounded-xl animate-pulse bg-slate-700/40"
                    />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {scorecardGauges.map((g) => (
                    <ScorecardGauge key={g.label} {...g} />
                  ))}
                </div>
              )}

              {/* Evolution status row */}
              <div
                className="flex items-center justify-between px-3 py-2 rounded-lg border"
                style={{
                  background: "var(--os-surface-2)",
                  borderColor: "var(--os-stroke)",
                }}
              >
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">
                    Evolution
                  </p>
                  <p
                    className={`text-xs font-semibold mt-0.5 ${evolveHealthColor}`}
                  >
                    {evolveLoading
                      ? "checking…"
                      : evolveIsRunning
                        ? "running"
                        : evolveJobStatus}
                  </p>
                  {evolveLastRun && (
                    <p className="text-[9px] text-slate-600 font-mono mt-0.5">
                      last: {relTime(evolveLastRun)}
                    </p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={runEvolve}
                  loading={evolving}
                  disabled={evolveIsRunning}
                >
                  <PlayCircle size={13} className="mr-1" />
                  Run
                </Button>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div
            className="rounded-xl border overflow-hidden"
            style={{
              borderColor: "var(--os-stroke)",
              background: "var(--os-surface-1)",
            }}
          >
            <PanelHeader title="Quick Actions" />
            <div className="p-3 space-y-1.5">
              {QUICK_ACTIONS.map((qa) => (
                <button
                  key={qa.href}
                  onClick={() => router.push(qa.href)}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg border text-sm font-medium text-slate-300 hover:text-slate-100 hover:bg-slate-700/40 transition-all"
                  style={{ borderColor: "var(--os-stroke)" }}
                >
                  <span className="flex items-center gap-2.5">
                    <span className="text-slate-500">{qa.icon}</span>
                    {qa.label}
                  </span>
                  <ArrowRight size={13} className="text-slate-600" />
                </button>
              ))}

              {/* Upload button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg border text-sm font-medium text-slate-300 hover:text-slate-100 hover:bg-cyan-900/20 border-cyan-900/30 hover:border-cyan-700/50 transition-all disabled:opacity-50"
              >
                <span className="flex items-center gap-2.5">
                  <Upload size={14} className="text-cyan-600" />
                  {uploading ? "Uploading…" : "Upload to FAIM"}
                </span>
                <Sparkles size={13} className="text-cyan-700" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handleFileUpload(file);
                    e.target.value = "";
                  }
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Row 3 — Bottom Grid ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Storage Summary */}
        <div
          className="rounded-xl border overflow-hidden"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Storage Breakdown"
            action={
              <button
                onClick={() => router.push("/dashboard/storage")}
                className="text-[10px] text-slate-500 hover:text-slate-300 flex items-center gap-1"
              >
                Manage <ArrowRight size={10} />
              </button>
            }
          />
          <div className="p-4 space-y-2.5">
            {storageLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="h-10 rounded-lg animate-pulse bg-slate-700/40"
                  />
                ))}
              </div>
            ) : (
              <>
                {[
                  {
                    label: "Total Used",
                    value: fmtBytes(storage?.total_bytes ?? 0),
                    icon: <HardDrive size={13} />,
                  },
                  {
                    label: "File Count",
                    value: String(storage?.total_files ?? 0),
                    icon: <Activity size={13} />,
                  },
                  {
                    label: "By Status",
                    value:
                      Object.keys(storage?.by_status ?? {}).join(", ") || "—",
                    icon: <Layers size={13} />,
                  },
                  {
                    label: "By Type",
                    value:
                      Object.keys(storage?.by_type ?? {})
                        .slice(0, 3)
                        .join(", ") || "—",
                    icon: <ShieldCheck size={13} />,
                  },
                ].map((row) => (
                  <div
                    key={row.label}
                    className="flex items-center justify-between px-3 py-2 rounded-lg border"
                    style={{
                      background: "var(--os-surface-2)",
                      borderColor: "var(--os-stroke)",
                    }}
                  >
                    <span className="flex items-center gap-2 text-slate-500">
                      {row.icon}
                      <span className="text-xs text-slate-400">
                        {row.label}
                      </span>
                    </span>
                    <span className="text-xs font-mono text-slate-100">
                      {row.value}
                    </span>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        {/* Security & Keys */}
        <div
          className="rounded-xl border overflow-hidden"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Security & Keys"
            action={
              <button
                onClick={() => router.push("/dashboard/api-keys")}
                className="text-[10px] text-slate-500 hover:text-slate-300 flex items-center gap-1"
              >
                Manage <ArrowRight size={10} />
              </button>
            }
          />
          <div className="p-4 space-y-3">
            {keysLoading ? (
              <div className="space-y-2">
                {[0, 1].map((i) => (
                  <div
                    key={i}
                    className="h-12 rounded-lg animate-pulse bg-slate-700/40"
                  />
                ))}
              </div>
            ) : (
              <>
                <div
                  className="flex items-center justify-between px-4 py-3 rounded-xl border"
                  style={{
                    background: "var(--os-surface-2)",
                    borderColor: "var(--os-stroke)",
                  }}
                >
                  <div className="flex items-center gap-3">
                    <KeyRound size={16} className="text-amber-400" />
                    <div>
                      <p className="text-xs font-semibold text-slate-200">
                        API Keys
                      </p>
                      <p className="text-[10px] text-slate-500">
                        {keyCount?.active ?? 0} active of {keyCount?.total ?? 0}{" "}
                        total
                      </p>
                    </div>
                  </div>
                  <div
                    className={`h-2 w-2 rounded-full ${(keyCount?.active ?? 0) > 0 ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" : "bg-slate-600"}`}
                  />
                </div>

                <div
                  className="flex items-center justify-between px-4 py-3 rounded-xl border"
                  style={{
                    background: "var(--os-surface-2)",
                    borderColor: "var(--os-stroke)",
                  }}
                >
                  <div className="flex items-center gap-3">
                    <Shield
                      size={16}
                      className={
                        healthOk ? "text-emerald-400" : "text-rose-400"
                      }
                    />
                    <div>
                      <p className="text-xs font-semibold text-slate-200">
                        System Status
                      </p>
                      <p className="text-[10px] text-slate-500">
                        {health?.status ?? "checking"}
                      </p>
                    </div>
                  </div>
                  <div
                    className={`h-2 w-2 rounded-full ${healthOk ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" : "bg-rose-400 animate-pulse"}`}
                  />
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  fullWidth
                  onClick={() => router.push("/dashboard/api-keys")}
                >
                  <KeyRound size={13} className="mr-1.5" />
                  Create New Key
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Evolution Status */}
        <div
          className="rounded-xl border overflow-hidden"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Evolution Engine"
            subtitle="FAIM graph self-organization"
          />
          <div className="p-4 space-y-3">
            {evolveLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="h-10 rounded-lg animate-pulse bg-slate-700/40"
                  />
                ))}
              </div>
            ) : (
              <>
                {[
                  {
                    label: "Status",
                    value: evolveIsRunning
                      ? "running"
                      : (evolveJobStatus ?? "—"),
                    color: evolveHealthColor,
                  },
                  {
                    label: "Last Run",
                    value: relTime(evolveLastRun),
                    color: "text-slate-300",
                  },
                  {
                    label: "Version Delta",
                    value: String(evolveStatus?.due?.version_delta ?? "—"),
                    color: "text-cyan-400",
                  },
                  {
                    label: "Due For Evolution",
                    value: evolveStatus?.due?.is_due
                      ? "Yes"
                      : evolveStatus
                        ? "No"
                        : "—",
                    color: evolveStatus?.due?.is_due
                      ? "text-amber-400"
                      : "text-emerald-400",
                  },
                ].map((row) => (
                  <div
                    key={row.label}
                    className="flex items-center justify-between px-3 py-2 rounded-lg border"
                    style={{
                      background: "var(--os-surface-2)",
                      borderColor: "var(--os-stroke)",
                    }}
                  >
                    <span className="text-xs text-slate-400">{row.label}</span>
                    <span
                      className={`text-xs font-mono font-semibold ${row.color}`}
                    >
                      {row.value}
                    </span>
                  </div>
                ))}

                <Button
                  variant="primary"
                  size="sm"
                  fullWidth
                  onClick={runEvolve}
                  loading={evolving}
                  disabled={evolveIsRunning}
                >
                  <PlayCircle size={14} className="mr-1.5" />
                  {evolveIsRunning ? "Running…" : "Run Evolution"}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
