"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Dna,
  GitMerge,
  Hash,
  Play,
  RefreshCw,
  Scissors,
  Sparkles,
} from "lucide-react";
import { getSession, useSession } from "next-auth/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Input,
  Select,
  useToast,
} from "@/components/ui";
import {
  buildEffectiveModeText,
  formatModePair,
  getPersistHelper,
  getProfileHelper,
  resolveUiModePolicy,
} from "@/lib/profilePersistModes";

type EvolveResponse = {
  status: string;
  graph_version: number;
  merges: number;
  prunes: number;
  inventions: number;
  diagnostics?: Record<string, unknown> | null;
  events_emitted: string[];
  latency_ms: number;
  requested_profile?: string | null;
  requested_persist_mode?: string | null;
  effective_profile?: string | null;
  effective_persist_mode?: string | null;
  durability_path?: string | null;
  evolve_aggressiveness?: string | null;
  completion_mode?: string | null;
  state_update_status?: string | null;
  state_update_error?: string | null;
  error?: string | null;
};

type MetricsScorecard = {
  graph_id: string;
  graph_version: number;
  graph_hash: string;
  dimension_D?: number | null;
  entropy_H?: number | null;
  pressure_lambda?: number | null;
  node_count: number;
  edge_count: number;
  redundancy?: number | null;
  novelty?: number | null;
  energy?: number | null;
  computed_at?: string | null;
};

type GraphEvent = {
  seq: number;
  id: string;
  kind: string;
  ts?: string | null;
  payload: Record<string, unknown>;
  checksum?: string | null;
};

type GraphEventsResponse = {
  graph_id: string;
  tenant_id: string;
  events: GraphEvent[];
  has_more: boolean;
  next_seq: number;
  count: number;
};

type LatestEventResponse = {
  graph_id: string;
  last_seq: number;
  last_kind?: string | null;
  last_ts?: string | null;
  snapshot_hash?: string | null;
  event_count: number;
};

type EvolveStatusRuntime = {
  self_evolve_enabled: boolean;
  self_evolve_trigger_mode: string;
  self_evolve_min_interval_seconds: number;
  self_evolve_min_version_delta: number;
  self_evolve_max_actions: number;
  self_evolve_scan_interval_seconds: number;
  self_invent_enabled: boolean;
  self_invent_on_evolve: boolean;
  jobs_enabled: boolean;
};

type EvolveStatusState = {
  graph_id: string;
  graph_version: number;
  last_seen_version: number;
  last_evolved_version: number;
  last_evolved_at?: string | null;
  last_enqueued_job_id?: string | null;
};

type EvolveStatusDue = {
  source: string;
  is_due: boolean;
  reason: string;
  graph_version: number;
  last_seen_version: number;
  last_evolved_version: number;
  version_delta: number;
  min_version_delta: number;
  min_interval_seconds: number;
  elapsed_since_last_evolved_seconds?: number | null;
};

type EvolveStatusJobSummary = {
  job_id: string;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  source?: string | null;
  trigger_graph_version?: number | null;
  trigger_version_delta?: number | null;
  self_invent_requested?: boolean | null;
};

type EvolveStatusLastEvent = {
  last_event_seq: number;
  last_event_kind?: string | null;
  last_event_ts?: string | null;
  last_snapshot_hash?: string | null;
  last_skip_reason?: string | null;
};

type EvolveStatusResponse = {
  graph_id: string;
  tenant_id: string;
  runtime: EvolveStatusRuntime;
  state: EvolveStatusState;
  due: EvolveStatusDue;
  active_job?: EvolveStatusJobSummary | null;
  last_enqueued_job?: EvolveStatusJobSummary | null;
  last_event: EvolveStatusLastEvent;
};

type StorageSummaryResponse = {
  graph_id?: string | null;
  total_files: number;
  total_bytes: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
};

type StorageFileItem = {
  raw_id: string;
  graph_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  ingest_status: string;
  packet_hash?: string | null;
  node_count: number;
  vector_count: number;
  error?: string | null;
  uploaded_at?: string | null;
  ingested_at?: string | null;
  updated_at?: string | null;
  delete_requested: boolean;
};

type StorageFileListResponse = {
  items: StorageFileItem[];
  total: number;
  limit: number;
  offset: number;
};

type LiveStatus = "idle" | "refreshing" | "live" | "error";

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const INITIAL_EVENT_LIMIT = 100;
const POLL_EVENT_LIMIT = 60;
const MAX_TIMELINE_EVENTS = 260;
const POLL_INTERVAL_MS = 2500;
const METRICS_REFRESH_EVERY_POLLS = 3;
const ENABLE_GRAPH_SWITCH =
  (process.env.NEXT_PUBLIC_FAIM_ENABLE_GRAPH_SWITCH || "").toLowerCase() === "true";

const EVOLUTION_EVENT_KINDS = new Set([
  "DIAGNOSTICS_SNAPSHOT",
  "EVOLUTION_START",
  "EVOLUTION_COMPLETE",
  "EVOLUTION_PERSISTENCE_APPLIED",
  "EVOLUTION_SKIPPED",
  "EVOLUTION_MERGE",
  "PRUNE_NODE",
  "EVOLUTION_INVENTION_SUMMARY",
  "EVOLUTION_INVENTION_ERROR",
]);

function normalizeApiError(payload: unknown, fallback: string): string {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (typeof payload === "object") {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    const error = (payload as { error?: unknown }).error;
    if (typeof error === "string" && error.trim()) return error;
  }
  return fallback;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function asString(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  return null;
}

function resolveEventModeText(payload: Record<string, unknown>): string {
  const requested = formatModePair(
    asString(payload.requested_profile),
    asString(payload.requested_persist_mode)
  );
  const effective = formatModePair(
    asString(payload.effective_profile),
    asString(payload.effective_persist_mode)
  );
  const durability = asString(payload.durability_path);
  if (requested === "-" && effective === "-" && !durability) return "";
  const durabilitySuffix = durability ? ` (${durability})` : "";
  return ` | mode ${requested} -> ${effective}${durabilitySuffix}`;
}

function shortHash(value?: string | null): string {
  if (!value) return "-";
  if (value.length <= 16) return value;
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

function formatTimestamp(value?: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatMetric(value: number | null | undefined, digits = 3): string {
  if (value == null || !Number.isFinite(value)) return "-";
  return value.toFixed(digits);
}

function formatCount(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "-";
  return Intl.NumberFormat().format(value);
}

function formatBytes(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "-";
  if (value < 1024) return `${value} B`;
  const kb = value / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  const gb = mb / 1024;
  return `${gb.toFixed(2)} GB`;
}

function humanizeDueReason(reason?: string | null): string {
  const text = (reason || "").trim();
  if (!text) return "-";
  if (text.startsWith("not_due_version_delta:")) {
    return text.replace(
      "not_due_version_delta:",
      "Not due: graph version delta below threshold ("
    ) + ")";
  }
  if (text.startsWith("not_due_interval:")) {
    return text.replace(
      "not_due_interval:",
      "Not due: minimum interval not reached ("
    ) + ")";
  }
  if (text === "active_evolve_job_exists") return "An evolve job is already pending/running.";
  if (text === "due_enqueued") return "Due and enqueued.";
  if (text.startsWith("unsupported_source:")) return `Unsupported source trigger (${text.split(":")[1] || "unknown"}).`;
  return text;
}

function dedupeAndSortEvents(events: GraphEvent[]): GraphEvent[] {
  const bySeq = new Map<number, GraphEvent>();
  for (const event of events) {
    if (typeof event.seq !== "number") continue;
    bySeq.set(event.seq, event);
  }
  return Array.from(bySeq.values()).sort((a, b) => a.seq - b.seq);
}

function mergeEvents(current: GraphEvent[], incoming: GraphEvent[]): GraphEvent[] {
  const merged = dedupeAndSortEvents([...current, ...incoming]);
  if (merged.length <= MAX_TIMELINE_EVENTS) return merged;
  return merged.slice(-MAX_TIMELINE_EVENTS);
}

function resolveInitialGraphId(sessionGraphId?: string): string {
  if (typeof window !== "undefined") {
    const universe = window.localStorage.getItem("faim.universe_graph_id");
    if (universe && universe.trim()) return universe.trim();
  }
  if (sessionGraphId && sessionGraphId.trim()) return sessionGraphId.trim();
  return "default";
}

function liveStatusVariant(
  status: LiveStatus
): "default" | "success" | "warning" | "error" | "info" {
  if (status === "live") return "success";
  if (status === "refreshing") return "info";
  if (status === "error") return "error";
  return "default";
}

function eventBadgeVariant(
  kind: string
): "default" | "primary" | "secondary" | "success" | "warning" | "error" | "info" | "outline" {
  if (kind === "EVOLUTION_COMPLETE") return "success";
  if (kind === "EVOLUTION_SKIPPED") return "warning";
  if (kind === "EVOLUTION_INVENTION_ERROR") return "error";
  if (kind === "EVOLUTION_INVENTION_SUMMARY") return "secondary";
  if (kind === "DIAGNOSTICS_SNAPSHOT") return "info";
  return "default";
}

function eventSummary(event: GraphEvent): string {
  const payload = event.payload || {};

  if (event.kind === "EVOLUTION_COMPLETE") {
    const merges = asNumber(payload.merges);
    const prunes = asNumber(payload.prunes);
    const inventions = asNumber(payload.inventions);
    return `Completed: merges=${merges ?? 0}, prunes=${prunes ?? 0}, inventions=${inventions ?? 0}${resolveEventModeText(payload)}`;
  }

  if (event.kind === "EVOLUTION_SKIPPED") {
    const reason = typeof payload.reason === "string" ? payload.reason : "unknown";
    return `Skipped: ${reason}${resolveEventModeText(payload)}`;
  }

  if (event.kind === "EVOLUTION_MERGE") {
    const winner = typeof payload.winner_id === "string" ? shortHash(payload.winner_id) : "-";
    const loser = typeof payload.loser_id === "string" ? shortHash(payload.loser_id) : "-";
    return `Merge: ${winner} <- ${loser}`;
  }

  if (event.kind === "PRUNE_NODE") {
    const nodeId = typeof payload.node_id === "string" ? shortHash(payload.node_id) : "-";
    const reason = typeof payload.reason === "string" ? payload.reason : "prune";
    return `Prune: ${nodeId} (${reason})`;
  }

  if (event.kind === "EVOLUTION_INVENTION_SUMMARY") {
    const count = asNumber(payload.inventions) ?? 0;
    const signatures = asNumber(payload.signatures_tracked) ?? 0;
    return `Invention: macros=${count}, signatures=${signatures}`;
  }

  if (event.kind === "EVOLUTION_INVENTION_ERROR") {
    const text = typeof payload.error === "string" ? payload.error : "Invention failed";
    return text;
  }

  if (event.kind === "DIAGNOSTICS_SNAPSHOT") {
    const metrics =
      payload.metrics && typeof payload.metrics === "object"
        ? (payload.metrics as Record<string, unknown>)
        : {};
    const d = asNumber(metrics.D);
    const h = asNumber(metrics.H);
    const lambda = asNumber(metrics.lambda);
    return `Diagnostics: D=${d?.toFixed(3) ?? "-"}, H=${h?.toFixed(3) ?? "-"}, λ=${lambda?.toFixed(3) ?? "-"}`;
  }

  if (typeof payload.message === "string" && payload.message.trim()) return payload.message;
  return event.kind;
}

async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const base: Record<string, string> = {};
  if (token) base.Authorization = `Bearer ${token}`;

  if (!extra) return base;

  if (extra instanceof Headers) {
    const merged = new Headers(base);
    extra.forEach((value, key) => merged.set(key, value));
    return merged;
  }

  if (Array.isArray(extra)) {
    const merged = new Headers(base);
    for (const [key, value] of extra) merged.set(key, value);
    return merged;
  }

  return { ...base, ...(extra as Record<string, string>) };
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await authHeaders(init?.headers);
  const response = await fetch(path, {
    ...init,
    headers,
    cache: "no-store",
  });

  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, normalizeApiError(payload, `Request failed (${response.status})`));
  }

  return ((payload as T) ?? ({} as T));
}

export default function EvolutionPage() {
  const { data: session } = useSession();
  const { toast } = useToast();

  const [graphId, setGraphId] = useState("default");
  const [graphDraft, setGraphDraft] = useState("default");
  const [profile, setProfile] = useState("strict");
  const [persistMode, setPersistMode] = useState("relaxed");
  const evolveModePolicy = useMemo(
    () => resolveUiModePolicy("evolve", profile, persistMode),
    [persistMode, profile]
  );
  const selectedModeLabel = useMemo(
    () => formatModePair(profile, persistMode),
    [persistMode, profile]
  );

  const [metrics, setMetrics] = useState<MetricsScorecard | null>(null);
  const [latest, setLatest] = useState<LatestEventResponse | null>(null);
  const [evolveStatus, setEvolveStatus] = useState<EvolveStatusResponse | null>(null);
  const [storageSummary, setStorageSummary] = useState<StorageSummaryResponse | null>(null);
  const [storageFiles, setStorageFiles] = useState<StorageFileItem[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<GraphEvent[]>([]);
  const [lastRun, setLastRun] = useState<EvolveResponse | null>(null);
  const [lastSeq, setLastSeq] = useState(0);

  const [loadingSnapshot, setLoadingSnapshot] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [liveStatus, setLiveStatus] = useState<LiveStatus>("idle");

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showEvolutionOnly, setShowEvolutionOnly] = useState(true);
  const [pollError, setPollError] = useState<string | null>(null);

  const initializedRef = useRef(false);
  const pollBusyRef = useRef(false);
  const lastSeqRef = useRef(0);
  const pollTickRef = useRef(0);

  useEffect(() => {
    lastSeqRef.current = lastSeq;
  }, [lastSeq]);

  useEffect(() => {
    if (initializedRef.current) return;
    const sessionGraphId = (session as { graphId?: string } | null)?.graphId;
    const initialGraph = resolveInitialGraphId(sessionGraphId);
    setGraphId(initialGraph);
    setGraphDraft(initialGraph);
    initializedRef.current = true;
  }, [session]);

  const fetchScorecard = useCallback(async (targetGraphId: string): Promise<MetricsScorecard> => {
    const params = new URLSearchParams({ graph_id: targetGraphId });
    return apiRequest<MetricsScorecard>(`/api/v1/metrics/scorecard?${params.toString()}`);
  }, []);

  const fetchLatest = useCallback(async (targetGraphId: string): Promise<LatestEventResponse> => {
    const params = new URLSearchParams({ graph_id: targetGraphId });
    return apiRequest<LatestEventResponse>(`/api/v1/events/latest?${params.toString()}`);
  }, []);

  const fetchEvolveStatus = useCallback(async (targetGraphId: string): Promise<EvolveStatusResponse> => {
    const params = new URLSearchParams({
      graph_id: targetGraphId,
      source: "memory_write",
    });
    return apiRequest<EvolveStatusResponse>(`/api/v1/evolve/status?${params.toString()}`);
  }, []);

  const fetchStorageSummary = useCallback(async (targetGraphId: string): Promise<StorageSummaryResponse> => {
    const params = new URLSearchParams({ graph_id: targetGraphId });
    return apiRequest<StorageSummaryResponse>(`/api/v1/storage/summary?${params.toString()}`);
  }, []);

  const fetchStorageFiles = useCallback(async (targetGraphId: string): Promise<StorageFileListResponse> => {
    const params = new URLSearchParams({
      graph_id: targetGraphId,
      limit: "5",
      offset: "0",
    });
    return apiRequest<StorageFileListResponse>(`/api/v1/storage/files?${params.toString()}`);
  }, []);

  const fetchEvents = useCallback(
    async (targetGraphId: string, afterSeq: number, limit: number): Promise<GraphEventsResponse> => {
      const params = new URLSearchParams({
        graph_id: targetGraphId,
        after_seq: String(Math.max(0, afterSeq)),
        limit: String(limit),
      });
      return apiRequest<GraphEventsResponse>(`/api/v1/events?${params.toString()}`);
    },
    []
  );

  const refreshAll = useCallback(
    async (targetGraphId: string) => {
      setLiveStatus("refreshing");
      setPollError(null);
      setLoadingSnapshot(true);
      setLoadingTimeline(true);

      try {
        const [scorecardData, latestData, statusData, summaryData, filesData] = await Promise.all([
          fetchScorecard(targetGraphId),
          fetchLatest(targetGraphId),
          fetchEvolveStatus(targetGraphId),
          fetchStorageSummary(targetGraphId),
          fetchStorageFiles(targetGraphId),
        ]);

        setMetrics(scorecardData);
        setLatest(latestData);
        setEvolveStatus(statusData);
        setStorageSummary(summaryData);
        setStorageFiles(filesData.items || []);
        setLoadingSnapshot(false);

        const eventsData = await fetchEvents(targetGraphId, 0, INITIAL_EVENT_LIMIT);
        const normalized = dedupeAndSortEvents(eventsData.events || []);
        const lastSeqValue =
          normalized.length > 0
            ? normalized[normalized.length - 1].seq
            : Math.max(0, Number(latestData.last_seq || 0));
        setTimelineEvents(normalized.slice(-MAX_TIMELINE_EVENTS));
        setLastSeq(lastSeqValue);
        setLiveStatus("live");
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load evolution data";
        setLiveStatus("error");
        setPollError(message);
        toast.error("Evolution page failed to load", message);
      } finally {
        setLoadingSnapshot(false);
        setLoadingTimeline(false);
      }
    },
    [fetchEvents, fetchEvolveStatus, fetchLatest, fetchScorecard, fetchStorageFiles, fetchStorageSummary, toast]
  );

  const pollOnce = useCallback(
    async (targetGraphId: string) => {
      try {
        const eventsData = await fetchEvents(targetGraphId, lastSeqRef.current, POLL_EVENT_LIMIT);
        const incoming = eventsData.events || [];

        if (incoming.length) {
          setTimelineEvents((current) => mergeEvents(current, incoming));
          const maxIncomingSeq = incoming.reduce((max, event) => Math.max(max, event.seq || 0), 0);
          if (maxIncomingSeq > 0) {
            setLastSeq((prev) => Math.max(prev, maxIncomingSeq));
          }
        } else if (eventsData.next_seq > 0) {
          setLastSeq((prev) => Math.max(prev, eventsData.next_seq));
        }

        const statusData = await fetchEvolveStatus(targetGraphId);
        setEvolveStatus(statusData);

        const containsEvolutionEvent = incoming.some((event) => EVOLUTION_EVENT_KINDS.has(event.kind));
        pollTickRef.current += 1;
        if (containsEvolutionEvent || pollTickRef.current % METRICS_REFRESH_EVERY_POLLS === 0) {
          const [scorecardData, latestData, summaryData, filesData] = await Promise.all([
            fetchScorecard(targetGraphId),
            fetchLatest(targetGraphId),
            fetchStorageSummary(targetGraphId),
            fetchStorageFiles(targetGraphId),
          ]);
          setMetrics(scorecardData);
          setLatest(latestData);
          setStorageSummary(summaryData);
          setStorageFiles(filesData.items || []);
        }

        setLiveStatus("live");
        setPollError(null);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Evolution polling failed";
        setLiveStatus("error");
        setPollError(message);
      }
    },
    [fetchEvents, fetchEvolveStatus, fetchLatest, fetchScorecard, fetchStorageFiles, fetchStorageSummary]
  );

  const runEvolve = useCallback(async () => {
    const targetGraph = graphId.trim();
    if (!targetGraph) {
      toast.info("Graph id is required.");
      return;
    }
    const modePolicy = resolveUiModePolicy("evolve", profile, persistMode);
    if (!modePolicy.supported) {
      toast.warning(
        "Unsupported mode combination",
        modePolicy.reason || "Choose a supported profile/persist mode."
      );
      return;
    }

    setRunLoading(true);
    try {
      const payload = {
        graph_id: targetGraph,
        profile,
        persist_mode: persistMode,
      };

      const result = await apiRequest<EvolveResponse>("/api/v1/evolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      setLastRun(result);
      const summary = `Status=${result.status}, merges=${result.merges}, prunes=${result.prunes}, inventions=${result.inventions}`;
      const modeText = buildEffectiveModeText(
        result.requested_profile,
        result.requested_persist_mode,
        result.effective_profile,
        result.effective_persist_mode,
        result.durability_path
      );
      toast.success("Evolution cycle finished", `${summary} | ${modeText}`);
      await refreshAll(targetGraph);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Evolution request failed";
      toast.error("Failed to run evolution", message);
    } finally {
      setRunLoading(false);
    }
  }, [graphId, persistMode, profile, refreshAll, toast]);

  const applyGraphId = useCallback(() => {
    const next = graphDraft.trim();
    if (!next) {
      toast.info("Please enter a graph id.");
      return;
    }
    if (next === graphId) {
      toast.info("Graph already applied.");
      return;
    }
    setGraphId(next);
  }, [graphDraft, graphId, toast]);

  const manualRefresh = useCallback(async () => {
    await refreshAll(graphId);
  }, [graphId, refreshAll]);

  useEffect(() => {
    const targetGraph = graphId.trim();
    if (!targetGraph) return;
    setTimelineEvents([]);
    setLastSeq(0);
    setLastRun(null);
    setEvolveStatus(null);
    setStorageSummary(null);
    setStorageFiles([]);
    pollTickRef.current = 0;
    void refreshAll(targetGraph);
  }, [graphId, refreshAll]);

  useEffect(() => {
    if (!autoRefresh) return;
    const targetGraph = graphId.trim();
    if (!targetGraph) return;

    const timer = window.setInterval(() => {
      if (pollBusyRef.current) return;
      pollBusyRef.current = true;
      void pollOnce(targetGraph).finally(() => {
        pollBusyRef.current = false;
      });
    }, POLL_INTERVAL_MS);

    return () => {
      window.clearInterval(timer);
    };
  }, [autoRefresh, graphId, pollOnce]);

  const evolutionEvents = useMemo(
    () => timelineEvents.filter((event) => EVOLUTION_EVENT_KINDS.has(event.kind)),
    [timelineEvents]
  );

  const visibleTimeline = useMemo(() => {
    const base = showEvolutionOnly ? evolutionEvents : timelineEvents;
    return [...base].sort((a, b) => b.seq - a.seq);
  }, [evolutionEvents, showEvolutionOnly, timelineEvents]);

  const eventStats = useMemo(() => {
    let completed = 0;
    let skipped = 0;
    let inventionSummary = 0;
    for (const event of evolutionEvents) {
      if (event.kind === "EVOLUTION_COMPLETE") completed += 1;
      if (event.kind === "EVOLUTION_SKIPPED") skipped += 1;
      if (event.kind === "EVOLUTION_INVENTION_SUMMARY") inventionSummary += 1;
    }
    return { completed, skipped, inventionSummary };
  }, [evolutionEvents]);

  const latestEvolutionEvent = useMemo(() => {
    return [...evolutionEvents]
      .reverse()
      .find((event) => event.kind === "EVOLUTION_COMPLETE" || event.kind === "EVOLUTION_SKIPPED");
  }, [evolutionEvents]);

  const profileOptions = [
    { value: "strict", label: "Strict" },
    { value: "fast", label: "Fast" },
    { value: "relaxed", label: "Relaxed" },
  ];

  const persistModeOptions = [
    { value: "relaxed", label: "Relaxed" },
    { value: "strict", label: "Strict" },
  ];

  return (
    <div className="space-y-6 pb-8 text-slate-100">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Dna className="h-5 w-5 text-cyan-300" />
            <h1 className="text-xl font-semibold text-slate-100">Evolution Control Plane</h1>
          </div>
          <p className="text-sm text-slate-400">
            Observe diagnostics, run evolve cycles, and inspect self-invention/prune activity for graph{" "}
            <span className="font-mono text-cyan-200">{graphId}</span>.
          </p>
        </div>
        <Badge variant={liveStatusVariant(liveStatus)} size="md">
          {liveStatus === "refreshing" ? "Refreshing" : liveStatus === "live" ? "Live" : liveStatus === "error" ? "Error" : "Idle"}
        </Badge>
      </header>

      <Card className="rounded-2xl">
        <CardHeader
          title="Run Controls"
          description="Manual evolve action plus runtime view controls. Existing backend contracts only."
        />
        <CardContent className="grid gap-4 pt-4 md:grid-cols-5">
          {ENABLE_GRAPH_SWITCH ? (
            <>
              <Input
                label="Graph id"
                value={graphDraft}
                onChange={(event) => setGraphDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    applyGraphId();
                  }
                }}
                containerClassName="md:col-span-2"
                helperText="Universe graph id (for example U:...)."
              />

              <div className="flex flex-col justify-end gap-2">
                <Button variant="outline" onClick={applyGraphId}>
                  Apply graph
                </Button>
              </div>
            </>
          ) : (
            <div className="md:col-span-3 rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <p className="text-xs text-slate-400">Graph</p>
              <p className="mt-1 font-mono text-sm text-cyan-200">{graphId}</p>
              <p className="mt-1 text-xs text-slate-400">
                Graph context is auto-bound to your signed-in session.
              </p>
            </div>
          )}

          <Select
            label="Profile"
            options={profileOptions}
            value={profile}
            onChange={setProfile}
            helperText={getProfileHelper(profile)}
            fullWidth
          />

          <Select
            label="Persist mode"
            options={persistModeOptions}
            value={persistMode}
            onChange={setPersistMode}
            helperText={getPersistHelper(persistMode)}
            fullWidth
          />

          <div className="md:col-span-5 flex flex-wrap items-center gap-2">
            <Button
              variant="primary"
              leftIcon={<Play size={14} />}
              loading={runLoading}
              disabled={!evolveModePolicy.supported}
              onClick={runEvolve}
            >
              Run evolve now
            </Button>
            <Button
              variant="outline"
              leftIcon={<RefreshCw size={14} />}
              loading={loadingSnapshot || loadingTimeline}
              onClick={manualRefresh}
            >
              Refresh
            </Button>
            <Button
              variant={autoRefresh ? "secondary" : "ghost"}
              onClick={() => setAutoRefresh((prev) => !prev)}
            >
              Auto refresh: {autoRefresh ? "On" : "Off"}
            </Button>
            <Button
              variant={showEvolutionOnly ? "secondary" : "ghost"}
              onClick={() => setShowEvolutionOnly((prev) => !prev)}
            >
              {showEvolutionOnly ? "Evolution events only" : "All graph events"}
            </Button>
          </div>

          <div className="md:col-span-5">
            <div
              className={`rounded-xl border p-3 text-xs ${
                evolveModePolicy.supported
                  ? "border-white/10 bg-white/[0.02] text-slate-300"
                  : "border-rose-400/35 bg-rose-500/10 text-rose-200"
              }`}
            >
              <p className="font-medium text-slate-200">
                Requested mode: <span className="font-mono">{selectedModeLabel}</span>
              </p>
              {evolveModePolicy.supported && (
                <p className="mt-1">Backend will return effective mode and durability for each run.</p>
              )}
              <p>{getProfileHelper(profile)}</p>
              <p>{getPersistHelper(persistMode)}</p>
              {!evolveModePolicy.supported && (
                <p className="mt-1">
                  {evolveModePolicy.reason || "Selected profile/persist combination is not supported."}
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="rounded-2xl">
          <CardHeader title="Fractal D" description="Dimension estimate" />
          <CardContent className="pt-4">
            <p className="text-2xl font-semibold text-cyan-200">{formatMetric(metrics?.dimension_D)}</p>
          </CardContent>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader title="Entropy H" description="Distribution entropy" />
          <CardContent className="pt-4">
            <p className="text-2xl font-semibold text-cyan-200">{formatMetric(metrics?.entropy_H)}</p>
          </CardContent>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader title="Pressure λ" description="Evolution pressure" />
          <CardContent className="pt-4">
            <p className="text-2xl font-semibold text-cyan-200">{formatMetric(metrics?.pressure_lambda)}</p>
          </CardContent>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader title="Node / Edge" description="Current graph footprint" />
          <CardContent className="pt-4">
            <p className="text-2xl font-semibold text-cyan-200">
              {formatCount(metrics?.node_count)} / {formatCount(metrics?.edge_count)}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-5">
        <Card className="self-start rounded-2xl lg:col-span-3">
          <CardHeader
            title="Evolution Timeline"
            description="Latest graph events and evolve/invention actions."
            action={
              <Badge variant="outline" size="sm">
                {visibleTimeline.length} items
              </Badge>
            }
          />
          <CardContent className="pt-4">
            {visibleTimeline.length === 0 ? (
              loadingTimeline ? (
                <p className="text-sm text-slate-400">Loading timeline...</p>
              ) : (
              <p className="text-sm text-slate-400">No events available for this graph yet.</p>
              )
            ) : (
              <div>
                {loadingTimeline && (
                  <p className="mb-2 text-xs text-slate-400">Refreshing timeline...</p>
                )}
                <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
                {visibleTimeline.map((event) => (
                  <div
                    key={event.seq}
                    className="rounded-xl border border-white/10 bg-white/[0.02] p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={eventBadgeVariant(event.kind)} size="sm">
                        {event.kind}
                      </Badge>
                      <Badge variant="outline" size="xs">
                        seq {event.seq}
                      </Badge>
                      <span className="text-xs text-slate-400">{formatTimestamp(event.ts)}</span>
                    </div>
                    <p className="mt-2 text-sm text-slate-200">{eventSummary(event)}</p>
                  </div>
                ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4 lg:col-span-2">
          <Card className="rounded-2xl">
            <CardHeader title="Latest Run Outcome" description="Result from manual evolve action." />
            <CardContent className="space-y-3 pt-4">
              {!lastRun ? (
                <p className="text-sm text-slate-400">No manual evolve run in this session yet.</p>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <Badge variant={lastRun.status === "completed" ? "success" : "warning"} size="sm">
                      {lastRun.status}
                    </Badge>
                    <span className="text-xs text-slate-400">v{lastRun.graph_version}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div className="rounded-lg border border-white/10 p-2">
                      <p className="text-slate-400">Merges</p>
                      <p className="font-semibold text-cyan-200">{lastRun.merges}</p>
                    </div>
                    <div className="rounded-lg border border-white/10 p-2">
                      <p className="text-slate-400">Prunes</p>
                      <p className="font-semibold text-cyan-200">{lastRun.prunes}</p>
                    </div>
                    <div className="rounded-lg border border-white/10 p-2">
                      <p className="text-slate-400">Inventions</p>
                      <p className="font-semibold text-cyan-200">{lastRun.inventions}</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400">Latency: {lastRun.latency_ms} ms</p>
                  <p className="text-xs text-cyan-200">
                    {buildEffectiveModeText(
                      lastRun.requested_profile,
                      lastRun.requested_persist_mode,
                      lastRun.effective_profile,
                      lastRun.effective_persist_mode,
                      lastRun.durability_path
                    )}
                  </p>
                  <p className="text-xs text-slate-400">
                    completion: {lastRun.completion_mode || "-"} | aggressiveness:{" "}
                    {lastRun.evolve_aggressiveness || "-"} | state update:{" "}
                    {lastRun.state_update_status || "-"}
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-2xl">
            <CardHeader title="Runtime Snapshot" description="Live diagnostics and event stream health." />
            <CardContent className="space-y-3 pt-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-slate-300">
                  <Hash size={14} className="text-cyan-300" />
                  Graph hash
                </span>
                <span className="font-mono text-xs text-slate-300">{shortHash(metrics?.graph_hash)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-slate-300">
                  <Clock3 size={14} className="text-cyan-300" />
                  Last diagnostics
                </span>
                <span className="text-xs text-slate-300">{formatTimestamp(metrics?.computed_at)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-slate-300">
                  <Activity size={14} className="text-cyan-300" />
                  Last seq / kind
                </span>
                <span className="text-xs text-slate-300">
                  {evolveStatus?.last_event?.last_event_seq ?? latest?.last_seq ?? 0} /{" "}
                  {evolveStatus?.last_event?.last_event_kind || latest?.last_kind || "-"}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-1">
                <div className="rounded-lg border border-white/10 p-2">
                  <p className="text-[11px] text-slate-400">Complete</p>
                  <p className="font-semibold text-emerald-300">{eventStats.completed}</p>
                </div>
                <div className="rounded-lg border border-white/10 p-2">
                  <p className="text-[11px] text-slate-400">Skipped</p>
                  <p className="font-semibold text-amber-300">{eventStats.skipped}</p>
                </div>
                <div className="rounded-lg border border-white/10 p-2">
                  <p className="text-[11px] text-slate-400">Invention</p>
                  <p className="font-semibold text-violet-300">{eventStats.inventionSummary}</p>
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <p className="text-xs text-slate-400">Latest evolve event</p>
                {latestEvolutionEvent ? (
                  <>
                    <p className="mt-1 text-sm text-slate-200">{eventSummary(latestEvolutionEvent)}</p>
                    <p className="mt-1 text-[11px] text-slate-400">{formatTimestamp(latestEvolutionEvent.ts)}</p>
                  </>
                ) : (
                  <p className="mt-1 text-sm text-slate-400">No evolve completion/skip event yet.</p>
                )}
              </div>

              {pollError && (
                <div className="rounded-xl border border-amber-400/25 bg-amber-500/10 p-3 text-xs text-amber-200">
                  <div className="flex items-start gap-2">
                    <AlertTriangle size={14} className="mt-0.5" />
                    <span>{pollError}</span>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-3 gap-2 pt-1 text-xs text-slate-400">
                <div className="inline-flex items-center gap-1">
                  <CheckCircle2 size={12} className="text-emerald-300" />
                  complete
                </div>
                <div className="inline-flex items-center gap-1">
                  <GitMerge size={12} className="text-cyan-300" />
                  merge/prune
                </div>
                <div className="inline-flex items-center gap-1">
                  <Sparkles size={12} className="text-violet-300" />
                  invention
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-2xl">
            <CardHeader
              title="Scheduler State"
              description="Step B runtime flags, due reason, and evolve job state."
            />
            <CardContent className="space-y-3 pt-4 text-sm">
              {!evolveStatus ? (
                <p className="text-sm text-slate-400">Loading scheduler state...</p>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Trigger mode</span>
                    <span className="font-mono text-xs text-slate-200">
                      {evolveStatus.runtime.self_evolve_trigger_mode}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Jobs enabled</span>
                    <Badge variant={evolveStatus.runtime.jobs_enabled ? "success" : "warning"} size="xs">
                      {evolveStatus.runtime.jobs_enabled ? "enabled" : "disabled"}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Self evolve / invent</span>
                    <span className="text-xs text-slate-200">
                      {evolveStatus.runtime.self_evolve_enabled ? "on" : "off"} /{" "}
                      {evolveStatus.runtime.self_invent_enabled ? "on" : "off"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Due now</span>
                    <Badge variant={evolveStatus.due.is_due ? "success" : "outline"} size="xs">
                      {evolveStatus.due.is_due ? "yes" : "no"}
                    </Badge>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                    <p className="text-xs text-slate-400">Due reason</p>
                    <p className="mt-1 text-xs text-slate-200">{humanizeDueReason(evolveStatus.due.reason)}</p>
                    <p className="mt-1 font-mono text-[11px] text-slate-500">{evolveStatus.due.reason}</p>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Version delta</span>
                    <span className="text-xs text-slate-200">
                      {evolveStatus.due.version_delta} / {evolveStatus.due.min_version_delta}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Last evolved</span>
                    <span className="text-xs text-slate-200">
                      {formatTimestamp(evolveStatus.state.last_evolved_at)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Active job</span>
                    <span className="text-xs text-slate-200">
                      {evolveStatus.active_job
                        ? `${evolveStatus.active_job.status} (${shortHash(evolveStatus.active_job.job_id)})`
                        : "none (idle)"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Last enqueued</span>
                    <span className="text-xs text-slate-200">
                      {evolveStatus.last_enqueued_job
                        ? `${evolveStatus.last_enqueued_job.status} (${shortHash(evolveStatus.last_enqueued_job.job_id)})`
                        : "none"}
                    </span>
                  </div>
                  {evolveStatus.last_event.last_skip_reason && (
                    <div className="rounded-xl border border-amber-400/25 bg-amber-500/10 p-3 text-xs text-amber-200">
                      Last skip reason: {evolveStatus.last_event.last_skip_reason}
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-2xl">
            <CardHeader title="Metric Details" description="Additional scorecard fields." />
            <CardContent className="space-y-2 pt-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Redundancy</span>
                <span className="text-slate-200">{formatMetric(metrics?.redundancy)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Novelty</span>
                <span className="text-slate-200">{formatMetric(metrics?.novelty)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-slate-400">
                  <Scissors size={13} className="text-cyan-300" />
                  Energy
                </span>
                <span className="text-slate-200">{formatMetric(metrics?.energy)}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-2xl">
            <CardHeader title="Source Coverage" description="Latest ingested files for this graph." />
            <CardContent className="space-y-3 pt-4 text-sm">
              {!storageSummary ? (
                <p className="text-sm text-slate-400">Loading source coverage...</p>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Files</span>
                    <span className="text-slate-200">{formatCount(storageSummary.total_files)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Total bytes</span>
                    <span className="text-slate-200">{formatBytes(storageSummary.total_bytes)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Ingested</span>
                    <span className="text-slate-200">
                      {formatCount(storageSummary.by_status?.ingested ?? 0)}
                    </span>
                  </div>
                </>
              )}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <p className="text-xs text-slate-400">Latest files</p>
                {storageFiles.length === 0 ? (
                  <p className="mt-1 text-xs text-slate-400">No files indexed for this graph.</p>
                ) : (
                  <div className="mt-2 max-h-40 space-y-2 overflow-y-auto pr-1">
                    {storageFiles.map((file) => (
                      <div
                        key={file.raw_id}
                        className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-2 py-1"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-xs text-slate-200">{file.filename}</p>
                          <p className="text-[11px] text-slate-400">
                            nodes {file.node_count} | vectors {file.vector_count}
                          </p>
                        </div>
                        <Badge variant={file.ingest_status === "ingested" ? "success" : "outline"} size="xs">
                          {file.ingest_status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
