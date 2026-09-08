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
  BookOpen,
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
import { MiniMap } from "@/components/dashboard/MiniMap";
import { StorageModalityChart } from "@/components/dashboard/StorageModalityChart";
import { TelemetryPoint, TelemetryVelocityChart } from "@/components/dashboard/TelemetryVelocityChart";
import { LatencyHeatmap } from "@/components/dashboard/LatencyHeatmap";
import { CacheHitRateRing } from "@/components/dashboard/CacheHitRateRing";
import { WorkerPoolStatus } from "@/components/dashboard/WorkerPoolStatus";
import { GPUUtilization } from "@/components/dashboard/GPUUtilization";
import { CommandCenterManual } from "@/components/manuals/CommandCenterManual";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useUser } from "@/contexts/UserContext";
import { readJsonSafely } from "@/lib/safeFetch";

// ─── Auth helper ──────────────────────────────────────────────────────────────

async function authHeaders(
  extra?: Record<string, string>,
): Promise<Record<string, string>> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const base: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};
  return { ...base, ...extra };
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScorecardData {
  node_count: number;
  edge_count: number;
  dimension_D?: number | null;
  entropy_H?: number | null;
  pressure_lambda?: number | null;
  graph_version?: number;
  computed_at?: string | null;
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

function numOrZero(...vals: unknown[]): number {
  for (const v of vals) {
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string") {
      const n = Number(v);
      if (Number.isFinite(n)) return n;
    }
  }
  return 0;
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
  accentColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  color: string;
  loading?: boolean;
  className?: string;
  accentColor?: string;
}) {
  return (
    <div
      className={`relative flex flex-col justify-center px-4 sm:px-6 py-4 border-slate-800/50 hover:bg-white/[0.02] transition-all ${className}`}
    >
      {/* Domain Studio accent bar — horizontal gradient at top */}
      {accentColor && (
        <div
          className="absolute inset-x-0 top-0 h-[2px]"
          style={{ background: `linear-gradient(90deg, ${accentColor}, transparent)` }}
        />
      )}
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-mono font-bold uppercase tracking-[0.22em] text-slate-500">
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
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/6 px-5 py-3 shrink-0">
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.22em] text-cyan-400 flex items-center gap-1.5">
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
  value: number | null;
  hint: string;
  color: string;
}) {
  return (
    <div className="relative overflow-hidden flex flex-col items-center justify-center gap-0.5 py-2.5 px-1.5 sm:px-3 rounded-[14px] border border-white/8 bg-white/[0.03] text-center transition-transform hover:scale-[1.02] min-w-0">
      {/* Domain Studio vertical accent bar */}
      <span
        className="pointer-events-none absolute left-0 top-0 h-full w-[2px]"
        style={{ background: `${color}88` }}
      />
      <span
        className="font-mono text-[15px] sm:text-[18px] font-bold truncate leading-tight"
        style={{ color }}
      >
        {value != null ? (value > 0 ? value.toFixed(2) : "0") : "—"}
      </span>
      <span className="text-[7.5px] sm:text-[9px] uppercase tracking-[0.14em] text-slate-400 truncate max-w-full font-medium leading-tight">
        {label}
      </span>
      <span
        className="text-[7px] sm:text-[8px] font-mono truncate max-w-full leading-tight"
        style={{ color, opacity: 0.75 }}
      >
        {value != null ? hint : "no snapshot"}
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
  const [streamReady, setStreamReady] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  // Pipeline / infra telemetry
  const [pipelineStats, setPipelineStats] = useState<{
    gpu_available: boolean;
    gpu_active: boolean;
    throughput: number;
    hot_cache_size: number;
    queue_depth: number;
    system_health: { redis: boolean; qdrant: boolean; encryption: boolean };
  } | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(true);
  const [cacheHitRate, setCacheHitRate] = useState<{ hitRate: number | null; total: number }>({
    hitRate: null,
    total: 0,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Recharts Time Series state
  const [healthHistory, setHealthHistory] = useState<GraphHealthPoint[]>([]);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPoint[]>([]);
  const [srMessage, setSrMessage] = useState("");

  // ── Shared event-ingest state (polling + SSE converge here) ──

  const lastSeqRef = useRef<number>(0);
  const eventsRef = useRef<FaimEvent[]>([]);
  const eventTsRef = useRef<number[]>([]);
  const streamHealthyRef = useRef<boolean>(false);

  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  const ingestEvents = useCallback(
    (incoming: FaimEvent[], opts: { replace?: boolean } = {}) => {
      if (!incoming.length) return;
      const sorted = [...incoming].sort((a, b) => b.seq - a.seq);
      const maxSeq = sorted[0].seq;
      lastSeqRef.current = Math.max(lastSeqRef.current, maxSeq);

      const current = eventsRef.current;
      const ids = new Set(current.map((e) => e.id));
      const fresh = opts.replace ? sorted : sorted.filter((e) => !ids.has(e.id));

      if (fresh.length) {
        const merged = opts.replace ? fresh : [...fresh, ...current];
        const trimmed = merged.slice(0, 50).sort((a, b) => b.seq - a.seq);
        eventsRef.current = trimmed;
        setEvents(trimmed);

        const now = Date.now();
        eventTsRef.current.push(...fresh.map(() => now));
        while (
          eventTsRef.current.length &&
          now - eventTsRef.current[0] > 60_000
        ) {
          eventTsRef.current.shift();
        }
        const velocity = eventTsRef.current.length;
        const timeStr = new Date().toLocaleTimeString([], {
          minute: "2-digit",
          second: "2-digit",
        });
        setTelemetryHistory((th) =>
          [...th, { seq: maxSeq, time: timeStr, velocity }].slice(-10),
        );
      }

      setLatestInfo((prev) => {
        if (prev && maxSeq <= prev.last_seq) return prev;
        const base = prev ?? {
          last_seq: 0,
          event_count: 0,
          last_kind: null,
          last_ts: null,
        };
        return {
          ...base,
          last_seq: maxSeq,
          last_kind: sorted[0].kind ?? base.last_kind,
          last_ts: sorted[0].ts ?? base.last_ts,
        };
      });
    },
    [],
  );

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

      const d = data.dimension_D ?? null;
      const h = data.entropy_H ?? null;
      const l = data.pressure_lambda ?? null;
      if (d != null || h != null || l != null) {
        const timeStr = data.computed_at
          ? new Date(data.computed_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })
          : new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            });
        setHealthHistory((prev) =>
          [
            ...prev,
            {
              time: timeStr,
              entropy: h ?? 0,
              density: d ?? 0,
              spectral_radius: l ?? 0,
            },
          ].slice(-10),
        );
      }
    } catch {
      // silent
    } finally {
      setScorecardLoading(false);
    }
  }, [graphId]);

  // Seed the spectrum chart with real historical DIAGNOSTICS_SNAPSHOT samples.
  const fetchScorecardHistory = useCallback(async () => {
    if (!graphId) return;
    try {
      const headers = await authHeaders();
      const res = await fetch(
        `/api/v1/events?graph_id=${graphId}&after_seq=0&limit=50`,
        { headers },
      );
      if (!res.ok) return;
      const data = await readJsonSafely<{ events?: FaimEvent[] }>(res);
      if (!data?.events?.length) return;
      const snapshots = data.events
        .filter((e) => e.kind === "DIAGNOSTICS_SNAPSHOT")
        .sort((a, b) => a.seq - b.seq)
        .slice(-10);
      if (!snapshots.length) return;
      const points = snapshots.map((e) => {
        const p = e.payload;
        const metrics = (p?.metrics ?? {}) as Record<string, unknown>;
        const ts = e.ts ?? new Date().toISOString();
        return {
          time: new Date(ts).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
          entropy: numOrZero(p?.H_hat, p?.H, metrics.H_hat, metrics.H),
          density: numOrZero(p?.D_hat, p?.D, metrics.D_hat, metrics.D),
          spectral_radius: numOrZero(
            p?.lambda_hat,
            p?.lambda,
            metrics.lambda_hat,
            metrics.lambda,
          ),
        };
      });
      setHealthHistory(points);
    } catch {
      // silent
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

  // Pipeline / infrastructure stats (gpu, queue, cache, throughput)
  const fetchPipelineStats = useCallback(async () => {
    try {
      const headers = await authHeaders();
      const res = await fetch("/api/v1/pipeline/stats", { headers });
      if (!res.ok) return;
      const data = await readJsonSafely<{
        gpu_available: boolean;
        gpu_active: boolean;
        throughput: number;
        hot_cache_size: number;
        queue_depth: number;
        system_health: { redis: boolean; qdrant: boolean; encryption: boolean };
      }>(res);
      if (!data) return;
      setPipelineStats(data);
    } catch {
      // silent
    } finally {
      setPipelineLoading(false);
    }
  }, []);

  // Cache hit rate from hot cache (via pipeline stats hot_cache_size is size, need hit rate)
  // For now we derive from query metrics - but no endpoint exposes it directly yet.
  // We'll expose a placeholder that can be enhanced when cache stats endpoint is added.
  const fetchCacheHitRate = useCallback(async () => {
    // No dedicated endpoint yet; when available, call /api/v1/cache/stats
    // For now, leave as null until backend exposes hit_rate
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
        lastSeqRef.current = Math.max(lastSeqRef.current, latest.last_seq);

        const afterSeq = since ?? Math.max(0, latest.last_seq - 30);
        const res = await fetch(
          `/api/v1/events?graph_id=${graphId}&after_seq=${afterSeq}&limit=30`,
          { headers },
        );
        if (!res.ok) return;
        const data = await readJsonSafely<{ events?: FaimEvent[] }>(res);
        if (!data) return;
        ingestEvents(data.events ?? [], { replace: since === undefined });
        if (since === undefined) setStreamReady(true);
      } catch {
        // silent
      } finally {
        setEventsLoading(false);
      }
    },
    [graphId, ingestEvents],
  );

  // ── Initial load ──

  useEffect(() => {
    if (!graphId) return;
    fetchScorecard();
    fetchScorecardHistory();
    fetchStorage();
    fetchEvolveStatus();
    fetchKeys();
    fetchHealth();
    fetchPipelineStats();
    fetchEvents();
  }, [
    graphId,
    fetchScorecard,
    fetchScorecardHistory,
    fetchStorage,
    fetchEvolveStatus,
    fetchKeys,
    fetchHealth,
    fetchPipelineStats,
    fetchEvents,
  ]);

  // ── Polling: SSE is the live channel; fallback polling covers gaps ──

  useEffect(() => {
    if (!graphId) return;
    // Fallback event catch-up only when the SSE stream is not healthy.
    const evtInterval = setInterval(() => {
      if (!streamHealthyRef.current) {
        fetchEvents(lastSeqRef.current);
      }
    }, 15_000);
    const slowInterval = setInterval(() => {
      fetchScorecard();
      fetchEvolveStatus();
      fetchStorage();
      fetchPipelineStats();
    }, 30_000);
    return () => {
      clearInterval(evtInterval);
      clearInterval(slowInterval);
    };
  }, [graphId, fetchEvents, fetchScorecard, fetchEvolveStatus, fetchStorage, fetchPipelineStats]);

  // ── Real-time SSE event stream (events/stream) ──

  useEffect(() => {
    if (!graphId || !streamReady) return;

    let cancelled = false;
    let retryTimer: number | null = null;
    let controller: AbortController | null = null;
    let afterSeq = lastSeqRef.current;

    const connect = async () => {
      try {
        while (!cancelled) {
          controller = new AbortController();
          const headers = await authHeaders({ Accept: "text/event-stream" });
          const response = await fetch(
            `/api/v1/events/stream?graph_id=${encodeURIComponent(
              graphId,
            )}&after_seq=${afterSeq}`,
            {
              method: "GET",
              headers,
              cache: "no-store",
              signal: controller.signal,
            },
          );
          if (!response.ok || !response.body) {
            throw new Error(`Event stream unavailable (${response.status})`);
          }
          streamHealthyRef.current = true;

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          let eventName = "";
          let eventData = "";

          const flush = () => {
            if (!eventName && !eventData) return;
            try {
              const payload = eventData ? JSON.parse(eventData) : null;
              const seq = typeof payload?.seq === "number" ? payload.seq : null;
              if (seq != null) afterSeq = Math.max(afterSeq, seq);
              if (
                eventName &&
                !["ping", "timeout", "disconnect"].includes(eventName)
              ) {
                ingestEvents(
                  [
                    {
                      seq: payload.seq as number,
                      id: payload.id as string,
                      kind: payload.kind ?? eventName,
                      ts: payload.ts ?? null,
                      payload: payload.payload ?? {},
                    },
                  ],
                  { replace: false },
                );
              }
            } catch {
              // ignore malformed event frames
            } finally {
              eventName = "";
              eventData = "";
            }
          };

          while (!cancelled) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let newlineIndex = buffer.indexOf("\n");
            while (newlineIndex >= 0) {
              const line = buffer.slice(0, newlineIndex).replace(/\r$/, "");
              buffer = buffer.slice(newlineIndex + 1);
              if (line === "") {
                flush();
              } else if (line.startsWith("event:")) {
                eventName = line.slice(6).trim();
              } else if (line.startsWith("data:")) {
                eventData = eventData
                  ? `${eventData}\n${line.slice(5).trimStart()}`
                  : line.slice(5).trimStart();
              }
              newlineIndex = buffer.indexOf("\n");
            }
          }
        }
      } catch {
        streamHealthyRef.current = false;
        if (!cancelled) {
          retryTimer = window.setTimeout(() => {
            void connect();
          }, 3000);
        }
      }
    };

    void connect();
    return () => {
      cancelled = true;
      controller?.abort();
      if (retryTimer) window.clearTimeout(retryTimer);
    };
  }, [graphId, streamReady, ingestEvents]);

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
    const d = scorecard?.dimension_D ?? null;
    const h = scorecard?.entropy_H ?? null;
    const l = scorecard?.pressure_lambda ?? null;
    return [
      {
        label: "D — Density",
        value: d,
        hint: d != null && d >= 0.15 ? "dense" : d != null && d >= 0.05 ? "sparse" : "disconnected",
        color: d != null && d >= 0.15 ? "#22d3ee" : d != null && d >= 0.05 ? "#fbbf24" : "#64748b",
      },
      {
        label: "H — Entropy",
        value: h,
        hint: h != null && h >= 0.8 ? "diverse" : h != null && h >= 0.3 ? "moderate" : "uniform",
        color: h != null && h >= 0.8 ? "#a78bfa" : h != null && h >= 0.3 ? "#fbbf24" : "#64748b",
      },
      {
        label: "λ — Spectral",
        value: l,
        hint: l != null && l >= 2.0 ? "clustered" : l != null && l >= 0.5 ? "moderate" : "sparse",
        color: l != null && l >= 2.0 ? "#34d399" : l != null && l >= 0.5 ? "#fbbf24" : "#64748b",
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
      href: "/dashboard/graph",
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
    <>
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
              leftIcon={<BookOpen size={13} />}
              aria-label="Open Command Center user manual"
              onClick={() => setManualOpen(true)}
            >
              User Manual
            </Button>
            <Button
              size="sm"
              variant="outline"
              aria-label="Refresh dashboard metrics"
              onClick={() => {
                fetchScorecard();
                fetchScorecardHistory();
                fetchStorage();
                fetchEvolveStatus();
                fetchKeys();
                fetchHealth();
                fetchPipelineStats();
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
      <div className="grid grid-cols-2 xl:grid-cols-4 overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
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
          accentColor="#22d3ee"
        />
        <KpiCell
          icon={<HardDrive size={18} />}
          label="Storage Used"
          value={storageLoading ? "…" : fmtBytes(storage?.total_bytes ?? 0)}
          sub={`${storage?.total_files ?? "—"} files`}
          color="text-emerald-400"
          loading={storageLoading}
          className="border-l"
          accentColor="#34d399"
        />
        <KpiCell
          icon={<Shield size={18} />}
          label="API Keys"
          value={keysLoading ? "…" : String(keyCount?.total ?? 0)}
          sub={`${keyCount?.active ?? "—"} active`}
          color="text-amber-400"
          loading={keysLoading}
          className="border-t xl:border-t-0 xl:border-l"
          accentColor="#fbbf24"
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
          accentColor={healthOk ? "#34d399" : "#f87171"}
        />
      </div>

      {/* ── Row 2: Topology & Cortex 3D Visualizer Row ────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
        {/* Left Column (8 cols): Graph Topology Spectrum + Event Ingestion Velocity */}
        <div className="lg:col-span-8 flex flex-col gap-4">
          {/* Graph Topology Spectrum Chart */}
          <div className="rounded-[18px] border border-white/8 p-4 sm:p-5 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] flex flex-col justify-between">
            <PanelHeader
              title="Graph Topology Spectrum"
              subtitle="Real-time spectral radius (λ), density (D), and entropy (H) dynamics"
              action={
                scorecard?.graph_version != null && (
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/40 px-2 py-0.5 rounded">
                    Graph v{scorecard.graph_version}
                  </span>
                )
              }
            />
            <div className="mt-3 flex-1 min-h-[260px]">
              <GraphHealthChart data={healthHistory} />
            </div>
          </div>

          {/* Event Ingestion & Velocity Trend Card */}
          <div className="rounded-[18px] border border-white/8 p-4 sm:p-5 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] flex flex-col justify-between">
            <PanelHeader
              title="Event Ingestion & Velocity Trend"
              subtitle="Real-time event throughput telemetry (events / min)"
              action={
                latestInfo && (
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/40 px-2 py-0.5 rounded">
                    seq #{latestInfo.last_seq} · {latestInfo.event_count} total
                  </span>
                )
              }
            />
            <div className="mt-2 flex-1 min-h-[120px]">
              <TelemetryVelocityChart data={telemetryHistory} />
            </div>
          </div>
        </div>

        {/* Right Column (4 cols): 3D Cortex FIG Visualizer + Topology Gauges */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          {/* Live 3D FIG Canvas Preview */}
          <div className="rounded-[18px] border border-white/8 p-4 sm:p-5 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] flex flex-col justify-between flex-1">
            <PanelHeader
              title="Live Cortex 3D Graph"
              subtitle="Realtime Node-Link spatial cluster preview"
              action={
                <button
                  onClick={() => router.push("/dashboard/graph")}
                  className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
                >
                  Inspect <ArrowRight size={10} />
                </button>
              }
            />
            <div className="mt-3 flex-1 min-h-[260px]">
              <MiniFigCanvas
                graphId={graphId}
                nodeCount={scorecard?.node_count}
                edgeCount={scorecard?.edge_count}
              />
            </div>
          </div>

          {/* Topology Metrics Scorecard */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] p-1">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-cyan-400/60 via-cyan-400/20 to-transparent" />
            <PanelHeader
              title="Topology Metrics"
              subtitle="Scorecard gauges — D / H / λ"
            />
            <div className="p-3 sm:p-4">
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
            </div>
          </div>
        </div>
      </div>

      {/* ── Row 3: Balanced 3-Column Operational & Pipeline Grid ────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 items-start">
        {/* ── Column 1: Live Activity Stream + Quick Command Matrix ── */}
        <div className="flex flex-col gap-4">
          {/* Live Activity Log Feed */}
          <div className="flex flex-col rounded-[18px] border border-white/8 overflow-hidden bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <PanelHeader
              title="Live Activity Stream"
              subtitle="Real-time graph events via SSE stream"
            />
            <div className="max-h-[340px] overflow-y-auto custom-scrollbar">
              {eventsLoading ? (
                <div className="flex flex-col gap-0">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="px-5 py-4 border-b border-white/6"
                    >
                      <div className="h-4 w-3/4 rounded animate-pulse bg-slate-700/40" />
                    </div>
                  ))}
                </div>
              ) : events.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-8 gap-3 text-slate-500">
                  <Activity size={28} className="opacity-30" />
                  <p className="text-xs font-mono">
                    No events yet — ingest data to see activity
                  </p>
                </div>
              ) : (
                events.map((ev) => {
                  const meta = eventMeta(ev.kind);
                  return (
                    <div
                      key={ev.id}
                      className="group px-4 py-3 border-b border-white/6 last:border-0 transition-all hover:bg-white/[0.02]"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <span
                            className={`text-[9px] font-black uppercase tracking-[0.12em] w-14 shrink-0 ${meta.color}`}
                          >
                            {meta.label}
                          </span>
                          <p className="text-xs text-slate-200 font-medium truncate font-mono">
                            {eventSummary(ev)}
                          </p>
                        </div>
                        <span className="text-[9px] text-slate-500 font-mono shrink-0">
                          {relTime(ev.ts)}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Quick Command Matrix */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-violet-400/60 via-violet-400/20 to-transparent" />
            <PanelHeader title="Quick Command Matrix" />
            <div className="p-3 space-y-1.5">
              {QUICK_ACTIONS.map((qa) => (
                <button
                  key={qa.href}
                  onClick={() => router.push(qa.href)}
                  aria-label={qa.label}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-white/8 text-xs font-medium text-slate-300 hover:text-slate-100 hover:bg-white/[0.03] focus-visible:ring-2 focus-visible:ring-cyan-500 transition-all"
                >
                  <span className="flex items-center gap-2">
                    <span className="text-cyan-400">{qa.icon}</span>
                    {qa.label}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono text-slate-500 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                      {qa.keyHint}
                    </span>
                    <ArrowRight size={12} className="text-slate-600" />
                  </div>
                </button>
              ))}

              {/* Upload button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                aria-label="Upload document to FAIM"
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg border text-xs font-medium text-slate-300 hover:text-slate-100 hover:bg-cyan-950/40 border-cyan-800/40 hover:border-cyan-500/50 focus-visible:ring-2 focus-visible:ring-cyan-500 transition-all disabled:opacity-50"
              >
                <span className="flex items-center gap-2">
                  <Upload size={13} className="text-cyan-400" />
                  {uploading ? "Uploading…" : "Upload to FAIM"}
                </span>
                <Sparkles size={12} className="text-cyan-400" />
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

        {/* ── Column 2: Compute Engine, Workers & GPU ── */}
        <div className="flex flex-col gap-4">
          {/* Evolution Engine Panel */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-emerald-400/60 via-emerald-400/20 to-transparent" />
            <PanelHeader
              title="Evolution Engine"
              subtitle="FAIM graph self-organization"
            />
            <div className="p-3.5 space-y-3">
              <div className="flex items-center justify-between px-4 py-3 rounded-[14px] border border-white/8 bg-white/[0.03]">
                <div>
                  <p className="text-[9px] uppercase tracking-widest text-slate-400 font-bold">
                    Status
                  </p>
                  <p className={`text-xs font-semibold ${evolveHealthColor}`}>
                    {evolveLoading
                      ? "checking…"
                      : evolveIsRunning
                        ? "running"
                        : evolveJobStatus}
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={runEvolve}
                  loading={evolving}
                  disabled={evolveIsRunning}
                >
                  <PlayCircle size={13} className="mr-1" />
                  {evolveIsRunning ? "Running…" : "Run Evolution"}
                </Button>
              </div>
            </div>
          </div>

          {/* Worker Pool Status */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] p-4">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-emerald-400/60 via-emerald-400/20 to-transparent" />
            <WorkerPoolStatus
              evolution={evolveStatus ? { is_running: evolveStatus.runtime?.is_running ?? false, worker_count: evolveStatus.runtime?.worker_count } : null}
              pipeline={pipelineStats ? { queue_depth: pipelineStats.queue_depth, throughput: pipelineStats.throughput, gpu_active: pipelineStats.gpu_active, system_health: pipelineStats.system_health } : null}
            />
          </div>

          {/* GPU Utilization */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] p-4">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-amber-400/60 via-amber-400/20 to-transparent" />
            <GPUUtilization
              gpuAvailable={pipelineStats?.gpu_available ?? false}
              gpuActive={pipelineStats?.gpu_active ?? false}
              throughput={pipelineStats?.throughput ?? 0}
            />
          </div>

          {/* Security & Auth Keys */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-amber-400/60 via-amber-400/20 to-transparent" />
            <PanelHeader
              title="Security & Auth Keys"
              action={
                <button
                  onClick={() => router.push("/dashboard/api-keys")}
                  className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono"
                >
                  Manage <ArrowRight size={10} />
                </button>
              }
            />
            <div className="p-3.5">
              <div className="flex items-center justify-between px-3 py-2 rounded-[14px] border border-white/8 bg-white/[0.03]">
                <div className="flex items-center gap-2.5">
                  <KeyRound size={14} className="text-amber-400" />
                  <span className="text-xs font-semibold text-slate-200">
                    {keyCount?.active ?? 0} active keys
                  </span>
                </div>
                <div
                  className={`h-2 w-2 rounded-full ${(keyCount?.active ?? 0) > 0 ? "bg-emerald-400" : "bg-slate-600"}`}
                />
              </div>
            </div>
          </div>
        </div>

        {/* ── Column 3: Storage, MiniMap, Pipeline Latency & Cache ── */}
        <div className="flex flex-col gap-4">
          {/* Storage Modality Breakdown */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] p-4">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-emerald-400/60 via-emerald-400/20 to-transparent" />
            <StorageModalityChart
              byType={storage?.by_type ?? {}}
              totalBytes={storage?.total_bytes ?? 0}
            />
          </div>

          {/* Mini-Map Bird's Eye */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] p-4">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-emerald-400/60 via-emerald-400/20 to-transparent" />
            <MiniMap graphId={graphId} />
          </div>

          {/* Pipeline Latency / Health Heatmap */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] p-4">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-cyan-400/60 via-cyan-400/20 to-transparent" />
            <LatencyHeatmap data={pipelineStats} />
          </div>

          {/* Cache Hit Rate */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] p-4">
            <span className="pointer-events-none absolute left-0 top-0 h-full w-[2px] bg-gradient-to-b from-violet-400/60 via-violet-400/20 to-transparent" />
            <CacheHitRateRing
              hitRate={cacheHitRate.hitRate}
              totalRequests={cacheHitRate.total}
              label="Cache Hit Rate"
            />
          </div>
        </div>
      </div>
    </div>

    <CommandCenterManual
      open={manualOpen}
      onClose={() => setManualOpen(false)}
    />
  </>
);
}
