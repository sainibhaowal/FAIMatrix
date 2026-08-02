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

import { GraphHealthChart, GraphHealthPoint } from "@/components/dashboard/GraphHealthChart";
import { MiniFigCanvas } from "@/components/dashboard/MiniFigCanvas";
import { StorageModalityChart } from "@/components/dashboard/StorageModalityChart";
import { TelemetryPoint, TelemetryVelocityChart } from "@/components/dashboard/TelemetryVelocityChart";
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
      className={`relative flex flex-col justify-center px-4 sm:px-6 py-4 border-slate-800/50 hover:bg-slate-800/20 transition-all ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-400">
          {label}
        </p>
        <div className="opacity-40">{icon}</div>
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
        <p className="text-[10px] font-black uppercase tracking-widest text-cyan-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
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
      className="flex flex-col items-center justify-center gap-0.5 py-3 px-2 sm:px-4 rounded-xl border text-center transition-transform hover:scale-[1.02]"
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

  // Recharts Time Series state
  const [healthHistory, setHealthHistory] = useState<GraphHealthPoint[]>([]);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPoint[]>([]);
  const [srMessage, setSrMessage] = useState("");

  // ── Fetch fns ──

  const fetchScorecard = useCallback(async () => {
    if (!graphId) return;
    try {
      const headers = await authHeaders();
      const res = await fetch(`/api/v1/metrics/scorecard?graph_id=${graphId}`, {
        headers,
      });
      if (!res.ok) return;
      const data = await readJsonSafely<ScorecardData>(res);
      if (!data) return;
      setScorecard(data);

      const timeStr = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      setHealthHistory((prev) =>
        [
          ...prev,
          {
            time: timeStr,
            entropy: data.entropy ?? 0,
            density: data.density ?? 0,
            spectral_radius: data.spectral_radius ?? 0,
          },
        ].slice(-10),
      );
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
      const data = await readJsonSafely<StorageSummary>(res);
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
      const data = await readJsonSafely<EvolveStatusResponse>(res);
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
      const data = await readJsonSafely<HealthData>(res);
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

          const updated = [...newOnes, ...prev]
            .slice(0, 50)
            .sort((a, b) => b.seq - a.seq);

          const timeStr = new Date().toLocaleTimeString([], {
            minute: "2-digit",
            second: "2-digit",
          });
          setTelemetryHistory((th) =>
            [
              ...th,
              {
                seq: latest.last_seq,
                time: timeStr,
                velocity: newOnes.length,
              },
            ].slice(-10),
          );

          return updated;
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
    setSrMessage("Triggering FAIM graph evolution...");
    try {
      const headers = await authHeaders();
      await fetch(`/api/v1/evolve`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ graph_id: graphId, profile: "strict" }),
      });
      setSrMessage("Evolution job submitted successfully.");
      setTimeout(() => {
        fetchEvolveStatus();
        fetchScorecard();
        fetchEvents(lastSeqRef.current);
      }, 2000);
    } catch {
      setSrMessage("Failed to submit evolution job.");
    } finally {
      setTimeout(() => setEvolving(false), 3000);
    }
  }, [graphId, evolving, fetchEvolveStatus, fetchScorecard, fetchEvents]);

  // ── Upload action ──

  const handleFileUpload = useCallback(
    async (file: File) => {
      if (!graphId || uploading) return;
      setUploading(true);
      setSrMessage(`Uploading file ${file.name} to FAIM...`);
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
        setSrMessage(`File ${file.name} uploaded successfully.`);
        setTimeout(() => {
          fetchStorage();
          fetchEvents(lastSeqRef.current);
        }, 1500);
      } catch {
        setSrMessage(`Failed to upload file ${file.name}.`);
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
      keyHint: "⌘G",
    },
    {
      label: "FAIM Cortex",
      icon: <Brain size={14} />,
      href: "/dashboard/memory-query",
      keyHint: "⌘M",
    },
    {
      label: "View Journal",
      icon: <Activity size={14} />,
      href: "/dashboard/journal",
      keyHint: "⌘J",
    },
    {
      label: "API Keys",
      icon: <KeyRound size={14} />,
      href: "/dashboard/api-keys",
      keyHint: "⌘K",
    },
    {
      label: "Storage",
      icon: <HardDrive size={14} />,
      href: "/dashboard/storage",
      keyHint: "⌘S",
    },
  ];

  return (
    <div className="relative flex flex-col gap-5 pb-8 px-1 text-slate-100">
      <div className="faim-grid" />

      {/* Screen Reader Live Region */}
      <div className="sr-only" role="status" aria-live="polite">
        {srMessage}
      </div>

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
              aria-label="Refresh dashboard metrics"
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
        className="grid grid-cols-2 xl:grid-cols-4 overflow-hidden rounded-xl border backdrop-blur-md shadow-2xl"
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

      {/* ── Row 2 — Live Visual Analytics Suite (Recharts & 3D FIG Canvas) ──────── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Topology Dynamics Recharts Chart */}
        <div
          className="xl:col-span-7 rounded-xl border p-4 backdrop-blur-md flex flex-col justify-between"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Graph Topology Spectrum"
            subtitle="Real-time spectral radius, density, and entropy dynamics"
            action={
              scorecard?.graph_version != null && (
                <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/40 px-2 py-0.5 rounded">
                  Graph v{scorecard.graph_version}
                </span>
              )
            }
          />
          <div className="mt-3 flex-1">
            <GraphHealthChart data={healthHistory} />
          </div>
        </div>

        {/* Live 3D FIG Canvas Preview */}
        <div
          className="xl:col-span-5 rounded-xl border p-4 backdrop-blur-md flex flex-col justify-between"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Live Cortex 3D Graph"
            subtitle="Realtime Node-Link cluster preview"
            action={
              <button
                onClick={() => router.push("/dashboard/fig-view")}
                className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
              >
                Inspect <ArrowRight size={10} />
              </button>
            }
          />
          <div className="mt-3 flex-1 min-h-[240px]">
            <MiniFigCanvas
              nodeCount={scorecard?.node_count}
              edgeCount={scorecard?.edge_count}
            />
          </div>
        </div>
      </div>

      {/* ── Row 3 — Main Activity & Operational Grid ─────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-start">
        {/* Activity Feed — 7 cols */}
        <div
          className="xl:col-span-7 flex flex-col rounded-xl border overflow-hidden backdrop-blur-md min-h-[220px] max-h-[480px]"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Live Telemetry & Activity Feed"
            subtitle="Real-time graph events — auto-updating every 10s"
            action={
              latestInfo && (
                <div className="flex items-center space-x-3">
                  <span className="text-[10px] font-mono text-slate-400">
                    seq #{latestInfo.last_seq} · {latestInfo.event_count} total
                  </span>
                  <div className="w-24 hidden sm:block">
                    <TelemetryVelocityChart data={telemetryHistory} />
                  </div>
                </div>
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
                <p className="text-sm font-mono">
                  No events yet — ingest data to see activity
                </p>
              </div>
            ) : (
              events.map((ev) => {
                const meta = eventMeta(ev.kind);
                return (
                  <div
                    key={ev.id}
                    className="group px-5 py-3 border-b last:border-0 transition-all hover:bg-slate-800/40"
                    style={{ borderColor: "var(--os-stroke)" }}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-4 min-w-0">
                        <span
                          className={`text-[10px] font-black uppercase tracking-[0.12em] w-16 shrink-0 ${meta.color}`}
                        >
                          {meta.label}
                        </span>
                        <p className="text-sm text-slate-200 font-medium truncate font-mono">
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

        {/* Right column: Scorecard Gauges & Quick Actions */}
        <div className="xl:col-span-5 flex flex-col gap-4">
          {/* Graph Scorecard Gauges */}
          <div
            className="rounded-xl border overflow-hidden backdrop-blur-md"
            style={{
              borderColor: "var(--os-stroke)",
              background: "var(--os-surface-1)",
            }}
          >
            <PanelHeader
              title="Topology Metrics"
              subtitle="Scorecard gauges — D / H / λ"
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
                <div className="grid grid-cols-3 gap-2">
                  {scorecardGauges.map((g) => (
                    <ScorecardGauge key={g.label} {...g} />
                  ))}
                </div>
              )}

              {/* Evolution status row */}
              <div
                className="flex items-center justify-between px-3.5 py-2.5 rounded-lg border"
                style={{
                  background: "var(--os-surface-2)",
                  borderColor: "var(--os-stroke)",
                }}
              >
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-slate-400 font-bold">
                    Evolution Engine
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
                    <p className="text-[9px] text-slate-500 font-mono mt-0.5">
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
            className="rounded-xl border overflow-hidden backdrop-blur-md"
            style={{
              borderColor: "var(--os-stroke)",
              background: "var(--os-surface-1)",
            }}
          >
            <PanelHeader title="Quick Command Matrix" />
            <div className="p-3 space-y-2">
              {QUICK_ACTIONS.map((qa) => (
                <button
                  key={qa.href}
                  onClick={() => router.push(qa.href)}
                  aria-label={qa.label}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg border text-sm font-medium text-slate-300 hover:text-slate-100 hover:bg-slate-800/60 focus-visible:ring-2 focus-visible:ring-cyan-500 transition-all"
                  style={{ borderColor: "var(--os-stroke)" }}
                >
                  <span className="flex items-center gap-2.5">
                    <span className="text-cyan-400">{qa.icon}</span>
                    {qa.label}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                      {qa.keyHint}
                    </span>
                    <ArrowRight size={13} className="text-slate-600" />
                  </div>
                </button>
              ))}

              {/* Upload button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                aria-label="Upload document to FAIM"
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg border text-sm font-medium text-slate-300 hover:text-slate-100 hover:bg-cyan-950/40 border-cyan-800/40 hover:border-cyan-500/50 focus-visible:ring-2 focus-visible:ring-cyan-500 transition-all disabled:opacity-50"
              >
                <span className="flex items-center gap-2.5">
                  <Upload size={14} className="text-cyan-400" />
                  {uploading ? "Uploading…" : "Upload to FAIM"}
                </span>
                <Sparkles size={13} className="text-cyan-400" />
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

      {/* ── Row 4 — Recharts Modality Breakdown & Operational Status ───────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Storage Breakdown Chart */}
        <div
          className="rounded-xl border overflow-hidden backdrop-blur-md"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Storage Breakdown"
            subtitle="Footprint per file type & status"
            action={
              <button
                onClick={() => router.push("/dashboard/storage")}
                className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
              >
                Manage <ArrowRight size={10} />
              </button>
            }
          />
          <div className="p-4 space-y-3">
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
                <StorageModalityChart
                  byType={storage?.by_type ?? {}}
                  totalBytes={storage?.total_bytes ?? 0}
                />
                <div className="grid grid-cols-2 gap-2 pt-2">
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800 text-center">
                    <p className="text-[10px] text-slate-500 font-mono">Total Size</p>
                    <p className="text-xs font-mono font-bold text-cyan-400">
                      {fmtBytes(storage?.total_bytes ?? 0)}
                    </p>
                  </div>
                  <div className="bg-slate-900/60 p-2 rounded border border-slate-800 text-center">
                    <p className="text-[10px] text-slate-500 font-mono">Files Count</p>
                    <p className="text-xs font-mono font-bold text-emerald-400">
                      {storage?.total_files ?? 0}
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Security & Keys */}
        <div
          className="rounded-xl border overflow-hidden backdrop-blur-md"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Security & Auth Keys"
            subtitle="Tenant key management & ACL status"
            action={
              <button
                onClick={() => router.push("/dashboard/api-keys")}
                className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
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
                      <p className="text-[10px] text-slate-500 font-mono">
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
                      <p className="text-[10px] text-slate-500 font-mono">
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
                  <KeyRound size={13} className="mr-1.5 text-amber-400" />
                  Create New Key
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Evolution Engine Details */}
        <div
          className="rounded-xl border overflow-hidden backdrop-blur-md"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <PanelHeader
            title="Evolution Engine"
            subtitle="FAIM graph self-organization telemetry"
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
                    <span className="text-xs text-slate-400 font-mono">{row.label}</span>
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
