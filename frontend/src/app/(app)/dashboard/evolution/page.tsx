"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  ChevronDown,
  Dna,
  GitMerge,
  Hash,
  Info,
  Play,
  RefreshCw,
  Scissors,
  Sparkles,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { getSession, useSession } from "next-auth/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GlassHeader } from "@/components/layout/GlassHeader";

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
import { useOutsideClick } from "@/components/ui";
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

type EvolveControlState = {
  self_evolve_enabled: boolean;
  self_evolve_trigger_mode: string;
  self_invent_enabled: boolean;
  self_invent_on_evolve: boolean;
  self_invent_after_upload: boolean;
  source: string;
  updated_at?: string | null;
  updated_by?: string | null;
  can_edit: boolean;
};

type EvolveStatusGuardrails = {
  self_evolve_enabled: boolean;
  self_invent_enabled: boolean;
  self_invent_on_evolve: boolean;
  self_invent_after_upload: boolean;
  jobs_enabled: boolean;
  trigger_mode: string;
  automation_path: string;
  automation_label: string;
  automation_enabled: boolean;
  guardrail_reason: string;
  control_source: string;
  control_updated_at?: string | null;
  control_updated_by?: string | null;
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
  control: EvolveControlState;
  guardrails: EvolveStatusGuardrails;
  state: EvolveStatusState;
  due: EvolveStatusDue;
  active_job?: EvolveStatusJobSummary | null;
  last_enqueued_job?: EvolveStatusJobSummary | null;
  last_event: EvolveStatusLastEvent;
};

// --- Custom Themed Select Component (Storage Parity) ---
function ThemedSelect<T extends string>({
  value,
  onChange,
  options,
  className = "",
  placeholder = "Select...",
  label = "",
}: {
  value: T;
  onChange: (val: T) => void;
  options: { value: T; label: string }[];
  className?: string;
  placeholder?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const current = options.find((o) => o.value === value);

  return (
    <div className={`relative ${className}`}>
      {label && (
        <p
          className="mb-1.5 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: "var(--text-tertiary)" }}
        >
          {label}
        </p>
      )}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex h-8 w-full items-center justify-between gap-2 rounded-lg border px-2.5 text-xs outline-none transition-all hover:bg-white/5 active:scale-[0.98]"
        style={{
          background: "rgba(255, 255, 255, 0.03)",
          borderColor: "rgba(255, 255, 255, 0.08)",
          color: "var(--text-primary)",
        }}
      >
        <span className="truncate">{current?.label || placeholder}</span>
        <ChevronDown
          size={14}
          className={`shrink-0 transition-transform duration-300 ${open ? "rotate-180" : ""}`}
          style={{ color: "var(--text-tertiary)" }}
        />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-[var(--z-modal)]"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -4 }}
              className="absolute left-0 top-full z-[var(--z-dropdown)] w-full min-w-[120px] mt-1 overflow-hidden rounded-xl border border-white/8 p-1 shadow-2xl backdrop-blur-xl"
              style={{
                background: "rgba(10, 15, 25, 0.96)",
                boxShadow: "0 10px 40px rgba(0,0,0,0.6)",
              }}
            >
              {options.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    onChange(opt.value);
                    setOpen(false);
                  }}
                  className={`flex h-8 w-full items-center rounded-lg px-2.5 text-xs transition-colors ${
                    opt.value === value
                      ? "bg-indigo-500/10 font-medium text-indigo-400"
                      : "text-[var(--text-secondary)] hover:bg-white/5"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

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
const POLL_INTERVAL_MS = 5000;
const METRICS_REFRESH_EVERY_POLLS = 3;
const ENABLE_GRAPH_SWITCH =
  (process.env.NEXT_PUBLIC_FAIM_ENABLE_GRAPH_SWITCH || "").toLowerCase() ===
  "true";

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
    asString(payload.requested_persist_mode),
  );
  const effective = formatModePair(
    asString(payload.effective_profile),
    asString(payload.effective_persist_mode),
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
    return (
      text.replace(
        "not_due_version_delta:",
        "Not due: graph version delta below threshold (",
      ) + ")"
    );
  }
  if (text.startsWith("not_due_interval:")) {
    return (
      text.replace(
        "not_due_interval:",
        "Not due: minimum interval not reached (",
      ) + ")"
    );
  }
  if (text === "active_evolve_job_exists")
    return "An evolve job is already pending/running.";
  if (text === "due_enqueued") return "Due and enqueued.";
  if (text === "self_evolve_disabled") return "Self-evolve is disabled.";
  if (text === "manual_mode") return "Manual mode only.";
  if (text === "post_upload_worker")
    return "Automation runs after uploads through the worker.";
  if (text === "periodic_worker")
    return "Automation runs periodically through the worker.";
  if (text === "hybrid_worker")
    return "Automation runs after uploads and on periodic scans.";
  if (text === "legacy_upload_compat")
    return "Legacy after-upload compatibility path is active.";
  if (text.startsWith("unsupported_source:"))
    return `Unsupported source trigger (${text.split(":")[1] || "unknown"}).`;
  return text;
}

function InfoTip({
  content,
  label,
  position = "left",
  className = "",
}: {
  content: React.ReactNode;
  label: string;
  position?: "left" | "right";
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [side, setSide] = useState<"left" | "right">(position);
  const ref = useRef<HTMLDivElement>(null);

  useOutsideClick(ref, () => setOpen(false), open);

  const openTip = () => {
    const rect = ref.current?.getBoundingClientRect();
    if (rect) {
      const idealWidth = Math.min(352, window.innerWidth - 32);
      const spaceRight = window.innerWidth - rect.left;
      const enoughRight = spaceRight >= idealWidth + 16;
      setSide(enoughRight ? "left" : "right");
    }
    setOpen((prev) => !prev);
  };

  return (
    <div ref={ref} className="relative inline-flex">
      <button
        type="button"
        aria-label={`${label} info`}
        aria-expanded={open}
        onClick={openTip}
        className={[
          "inline-flex h-6 w-6 items-center justify-center rounded-full border border-white/10",
          "bg-white/[0.03] text-slate-400 transition-colors hover:border-cyan-400/30 hover:bg-cyan-400/10 hover:text-cyan-200",
          "focus:outline-none focus:ring-2 focus:ring-cyan-400/30",
          className,
        ].join(" ")}
      >
        <Info size={12} />
      </button>

      {open && (
        <div
          className={[
            "absolute top-full z-30 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-2xl border",
            "border-cyan-400/15 bg-[#0b1220]/95 px-3 py-3 shadow-[0_18px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl",
            side === "left" ? "left-0" : "right-0",
          ].join(" ")}
        >
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-cyan-200">
            {label}
          </p>
          <div className="mt-1.5 text-[12px] leading-5 text-slate-200">
            {content}
          </div>
        </div>
      )}
    </div>
  );
}

function dedupeAndSortEvents(events: GraphEvent[]): GraphEvent[] {
  const bySeq = new Map<number, GraphEvent>();
  for (const event of events) {
    if (typeof event.seq !== "number") continue;
    bySeq.set(event.seq, event);
  }
  return Array.from(bySeq.values()).sort((a, b) => a.seq - b.seq);
}

function mergeEvents(
  current: GraphEvent[],
  incoming: GraphEvent[],
): GraphEvent[] {
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
  status: LiveStatus,
): "default" | "success" | "warning" | "error" | "info" {
  if (status === "live") return "success";
  if (status === "refreshing") return "info";
  if (status === "error") return "error";
  return "default";
}

function guardrailBadgeVariant(
  guardrails?: EvolveStatusGuardrails | null,
): "default" | "success" | "warning" | "error" | "info" | "outline" {
  if (!guardrails) return "outline";
  if (!guardrails.self_evolve_enabled && !guardrails.jobs_enabled) {
    return "outline";
  }
  if (guardrails.guardrail_reason === "legacy_upload_compat") {
    return "info";
  }
  if (!guardrails.automation_enabled) {
    return "warning";
  }
  return "success";
}

function modeChipVariant(active: boolean): "primary" | "secondary" | "outline" {
  return active ? "primary" : "outline";
}

function normalizeTriggerMode(value: string): string {
  const mode = value.trim().toLowerCase();
  if (["manual", "post_upload", "periodic", "hybrid"].includes(mode)) {
    return mode;
  }
  return "manual";
}

function normalizeInventState(
  next: "off" | "on_evolve" | "after_upload" | "both",
): Pick<
  EvolveControlState,
  "self_invent_enabled" | "self_invent_on_evolve" | "self_invent_after_upload"
> {
  switch (next) {
    case "off":
      return {
        self_invent_enabled: false,
        self_invent_on_evolve: false,
        self_invent_after_upload: false,
      };
    case "on_evolve":
      return {
        self_invent_enabled: true,
        self_invent_on_evolve: true,
        self_invent_after_upload: false,
      };
    case "after_upload":
      return {
        self_invent_enabled: true,
        self_invent_on_evolve: false,
        self_invent_after_upload: true,
      };
    case "both":
    default:
      return {
        self_invent_enabled: true,
        self_invent_on_evolve: true,
        self_invent_after_upload: true,
      };
  }
}

function eventBadgeVariant(
  kind: string,
):
  | "default"
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "error"
  | "info"
  | "outline" {
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
    const reason =
      typeof payload.reason === "string" ? payload.reason : "unknown";
    return `Skipped: ${reason}${resolveEventModeText(payload)}`;
  }

  if (event.kind === "EVOLUTION_MERGE") {
    const winner =
      typeof payload.winner_id === "string"
        ? shortHash(payload.winner_id)
        : "-";
    const loser =
      typeof payload.loser_id === "string" ? shortHash(payload.loser_id) : "-";
    return `Merge: ${winner} <- ${loser}`;
  }

  if (event.kind === "PRUNE_NODE") {
    const nodeId =
      typeof payload.node_id === "string" ? shortHash(payload.node_id) : "-";
    const reason =
      typeof payload.reason === "string" ? payload.reason : "prune";
    return `Prune: ${nodeId} (${reason})`;
  }

  if (event.kind === "EVOLUTION_INVENTION_SUMMARY") {
    const count = asNumber(payload.inventions) ?? 0;
    const signatures = asNumber(payload.signatures_tracked) ?? 0;
    return `Invention: macros=${count}, signatures=${signatures}`;
  }

  if (event.kind === "EVOLUTION_INVENTION_ERROR") {
    const text =
      typeof payload.error === "string" ? payload.error : "Invention failed";
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

  if (typeof payload.message === "string" && payload.message.trim())
    return payload.message;
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
    throw new ApiError(
      response.status,
      normalizeApiError(payload, `Request failed (${response.status})`),
    );
  }

  return (payload as T) ?? ({} as T);
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
    [persistMode, profile],
  );
  const selectedModeLabel = useMemo(
    () => formatModePair(profile, persistMode),
    [persistMode, profile],
  );

  const [metrics, setMetrics] = useState<MetricsScorecard | null>(null);
  const [latest, setLatest] = useState<LatestEventResponse | null>(null);
  const [evolveStatus, setEvolveStatus] = useState<EvolveStatusResponse | null>(
    null,
  );
  const [controlDraft, setControlDraft] = useState<EvolveControlState | null>(
    null,
  );
  const [storageSummary, setStorageSummary] =
    useState<StorageSummaryResponse | null>(null);
  const [storageFiles, setStorageFiles] = useState<StorageFileItem[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<GraphEvent[]>([]);
  const [lastRun, setLastRun] = useState<EvolveResponse | null>(null);
  const [lastSeq, setLastSeq] = useState(0);

  const [loadingSnapshot, setLoadingSnapshot] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [controlSaving, setControlSaving] = useState(false);
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
    setControlDraft(evolveStatus?.control ?? null);
  }, [evolveStatus]);

  useEffect(() => {
    if (initializedRef.current) return;
    const sessionGraphId = (session as { graphId?: string } | null)?.graphId;
    const initialGraph = resolveInitialGraphId(sessionGraphId);
    setGraphId(initialGraph);
    setGraphDraft(initialGraph);
    initializedRef.current = true;
  }, [session]);

  const fetchScorecard = useCallback(
    async (targetGraphId: string): Promise<MetricsScorecard> => {
      const params = new URLSearchParams({ graph_id: targetGraphId });
      return apiRequest<MetricsScorecard>(
        `/api/v1/metrics/scorecard?${params.toString()}`,
      );
    },
    [],
  );

  const fetchLatest = useCallback(
    async (targetGraphId: string): Promise<LatestEventResponse> => {
      const params = new URLSearchParams({ graph_id: targetGraphId });
      return apiRequest<LatestEventResponse>(
        `/api/v1/events/latest?${params.toString()}`,
      );
    },
    [],
  );

  const fetchEvolveStatus = useCallback(
    async (targetGraphId: string): Promise<EvolveStatusResponse> => {
      const params = new URLSearchParams({
        graph_id: targetGraphId,
        source: "memory_write",
      });
      return apiRequest<EvolveStatusResponse>(
        `/api/v1/evolve/status?${params.toString()}`,
      );
    },
    [],
  );

  const updateEvolveControl = useCallback(
    async (patch: {
      self_evolve_enabled?: boolean;
      self_evolve_trigger_mode?: string;
      self_invent_enabled?: boolean;
      self_invent_on_evolve?: boolean;
      self_invent_after_upload?: boolean;
    }) => {
      const targetGraph = graphId.trim();
      if (!targetGraph) {
        toast.info("Graph id is required.");
        return;
      }

      const current = controlDraft ?? evolveStatus?.control;
      if (!current) {
        toast.info("Control state is still loading.");
        return;
      }
      if (!current.can_edit) {
        toast.warning(
          "Not allowed",
          "This session cannot change autonomy controls.",
        );
        return;
      }

      const next = {
        self_evolve_enabled:
          patch.self_evolve_enabled ?? current.self_evolve_enabled,
        self_evolve_trigger_mode: normalizeTriggerMode(
          patch.self_evolve_trigger_mode ?? current.self_evolve_trigger_mode,
        ),
        self_invent_enabled:
          patch.self_invent_enabled ?? current.self_invent_enabled,
        self_invent_on_evolve:
          patch.self_invent_on_evolve ?? current.self_invent_on_evolve,
        self_invent_after_upload:
          patch.self_invent_after_upload ?? current.self_invent_after_upload,
      };

      setControlSaving(true);
      try {
        const params = new URLSearchParams({ graph_id: targetGraph });
        const result = await apiRequest<EvolveStatusResponse>(
          `/api/v1/evolve/control?${params.toString()}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(next),
          },
        );
        setEvolveStatus(result);
        setControlDraft(result.control);
        toast.success("Autonomy controls updated", "Graph settings saved.");
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Update failed";
        toast.error("Failed to update autonomy controls", message);
      } finally {
        setControlSaving(false);
      }
    },
    [controlDraft, evolveStatus?.control, graphId, toast],
  );

  const fetchStorageSummary = useCallback(
    async (targetGraphId: string): Promise<StorageSummaryResponse> => {
      const params = new URLSearchParams({ graph_id: targetGraphId });
      return apiRequest<StorageSummaryResponse>(
        `/api/v1/storage/summary?${params.toString()}`,
      );
    },
    [],
  );

  const fetchStorageFiles = useCallback(
    async (targetGraphId: string): Promise<StorageFileListResponse> => {
      const params = new URLSearchParams({
        graph_id: targetGraphId,
        limit: "5",
        offset: "0",
      });
      return apiRequest<StorageFileListResponse>(
        `/api/v1/storage/files?${params.toString()}`,
      );
    },
    [],
  );

  const fetchEvents = useCallback(
    async (
      targetGraphId: string,
      afterSeq: number,
      limit: number,
    ): Promise<GraphEventsResponse> => {
      const params = new URLSearchParams({
        graph_id: targetGraphId,
        after_seq: String(Math.max(0, afterSeq)),
        limit: String(limit),
      });
      return apiRequest<GraphEventsResponse>(
        `/api/v1/events?${params.toString()}`,
      );
    },
    [],
  );

  const refreshAll = useCallback(
    async (targetGraphId: string) => {
      setLiveStatus("refreshing");
      setPollError(null);
      setLoadingSnapshot(true);
      setLoadingTimeline(true);

      try {
        const [scorecardData, latestData, statusData, summaryData, filesData] =
          await Promise.all([
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

        const eventsData = await fetchEvents(
          targetGraphId,
          0,
          INITIAL_EVENT_LIMIT,
        );
        const normalized = dedupeAndSortEvents(eventsData.events || []);
        const lastSeqValue =
          normalized.length > 0
            ? normalized[normalized.length - 1].seq
            : Math.max(0, Number(latestData.last_seq || 0));
        setTimelineEvents(normalized.slice(-MAX_TIMELINE_EVENTS));
        setLastSeq(lastSeqValue);
        setLiveStatus("live");
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Failed to load evolution data";
        setLiveStatus("error");
        setPollError(message);
        toast.error("Evolution page failed to load", message);
      } finally {
        setLoadingSnapshot(false);
        setLoadingTimeline(false);
      }
    },
    [
      fetchEvents,
      fetchEvolveStatus,
      fetchLatest,
      fetchScorecard,
      fetchStorageFiles,
      fetchStorageSummary,
      toast,
    ],
  );

  const pollOnce = useCallback(
    async (targetGraphId: string) => {
      try {
        const eventsData = await fetchEvents(
          targetGraphId,
          lastSeqRef.current,
          POLL_EVENT_LIMIT,
        );
        const incoming = eventsData.events || [];

        if (incoming.length) {
          setTimelineEvents((current) => mergeEvents(current, incoming));
          const maxIncomingSeq = incoming.reduce(
            (max, event) => Math.max(max, event.seq || 0),
            0,
          );
          if (maxIncomingSeq > 0) {
            setLastSeq((prev) => Math.max(prev, maxIncomingSeq));
          }
        } else if (eventsData.next_seq > 0) {
          setLastSeq((prev) => Math.max(prev, eventsData.next_seq));
        }

        const statusData = await fetchEvolveStatus(targetGraphId);
        setEvolveStatus(statusData);

        const containsEvolutionEvent = incoming.some((event) =>
          EVOLUTION_EVENT_KINDS.has(event.kind),
        );
        pollTickRef.current += 1;
        if (
          containsEvolutionEvent ||
          pollTickRef.current % METRICS_REFRESH_EVERY_POLLS === 0
        ) {
          const [scorecardData, latestData, summaryData, filesData] =
            await Promise.all([
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
        const message =
          error instanceof Error ? error.message : "Evolution polling failed";
        setLiveStatus("error");
        setPollError(message);
      }
    },
    [
      fetchEvents,
      fetchEvolveStatus,
      fetchLatest,
      fetchScorecard,
      fetchStorageFiles,
      fetchStorageSummary,
    ],
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
        modePolicy.reason || "Choose a supported profile/persist mode.",
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
        result.durability_path,
      );
      toast.success("Evolution cycle finished", `${summary} | ${modeText}`);
      await refreshAll(targetGraph);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Evolution request failed";
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
    () =>
      timelineEvents.filter((event) => EVOLUTION_EVENT_KINDS.has(event.kind)),
    [timelineEvents],
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
      .find(
        (event) =>
          event.kind === "EVOLUTION_COMPLETE" ||
          event.kind === "EVOLUTION_SKIPPED",
      );
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
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader
        title="Evolution Control Plane"
        subtitle={`Observe diagnostics, run evolve cycles, and inspect self-invention for graph ${graphId}`}
        icon={Dna}
        titleTestId="evolution-page-title"
        actions={
          <Badge variant={liveStatusVariant(liveStatus)} size="md">
            {liveStatus === "refreshing"
              ? "Refreshing"
              : liveStatus === "live"
                ? "Live"
                : liveStatus === "error"
                  ? "Error"
                  : "Idle"}
          </Badge>
        }
      />

      <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] !overflow-visible">
        <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-cyan-500/80 via-cyan-400/40 to-transparent rounded-full" />
        <div className="border-b border-white/6 px-5 py-2.5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Run Controls
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Manual evolve action plus runtime view controls
              </p>
            </div>
            <InfoTip
              label="Run controls"
              content="This strip starts one evolve run on demand, refreshes the live graph state, and lets you choose which parts of the timeline you want to see."
            />
          </div>
        </div>
        <div className="grid gap-4 pt-5 px-5 pb-5 md:grid-cols-5">
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
                style={{
                  background: "rgba(255,255,255,0.03)",
                  borderColor: "rgba(255,255,255,0.08)",
                }}
                helperText="Universe graph id (for example U:...)."
              />

              <div className="flex flex-col justify-end gap-2">
                <Button variant="outline" onClick={applyGraphId}>
                  Apply graph
                </Button>
              </div>
            </>
          ) : (
            <div className="md:col-span-3 rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5">
              <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500">
                Graph Context
              </p>
              <p className="mt-1 font-mono text-sm text-cyan-200">{graphId}</p>
              <p className="mt-1 text-[11px] text-slate-400">
                Auto-bound to your signed-in session.
              </p>
            </div>
          )}

          <ThemedSelect
            label="Profile"
            options={profileOptions}
            value={profile}
            onChange={setProfile}
          />

          <ThemedSelect
            label="Persist mode"
            options={persistModeOptions}
            value={persistMode}
            onChange={setPersistMode}
          />

          <div className="md:col-span-5 flex flex-wrap items-center gap-2 mt-1">
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
              className={`rounded-[14px] border px-4 py-3 text-[11px] leading-relaxed ${
                evolveModePolicy.supported
                  ? ""
                  : "border-[var(--faim-error)]/30 bg-[var(--faim-error-muted)]"
              }`}
              style={
                evolveModePolicy.supported
                  ? {
                      borderColor: "rgba(99,102,241,0.22)",
                      background: "rgba(99,102,241,0.06)",
                      color: "var(--text-secondary)",
                    }
                  : { color: "var(--faim-error-text)" }
              }
            >
              <span style={{ color: "#818cf8", fontWeight: 500 }}>
                Requested mode: {selectedModeLabel}
              </span>
              {" · "}
              {getProfileHelper(profile)} {getPersistHelper(persistMode)}{" "}
              {evolveModePolicy.supported
                ? "Backend will return effective mode and durability for each run."
                : evolveModePolicy.reason}
            </div>
          </div>
        </div>
      </div>

      <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
        <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-cyan-500/80 via-cyan-400/40 to-transparent rounded-full" />
        <div className="border-b border-white/6 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-[10px] font-medium uppercase tracking-[0.35em] text-slate-500">
                  Autonomy Studio
                </p>
                <InfoTip
                  label="Autonomy studio"
                  content="This is the graph-level control surface. The left side edits what FAIM is allowed to do. The right side shows the live effective state after guardrails and runtime policy are applied."
                />
              </div>
              <p className="mt-1 text-sm text-slate-300">
                One control surface for self-evolve, self-invent, and the live
                effective state.
              </p>
            </div>
            <Badge
              variant={guardrailBadgeVariant(evolveStatus?.guardrails)}
              size="md"
            >
              {evolveStatus?.guardrails
                ? evolveStatus.guardrails.automation_enabled
                  ? "automation active"
                  : evolveStatus.guardrails.guardrail_reason ===
                        "legacy_upload_compat"
                    ? "legacy compat"
                    : "manual only"
                : "loading"}
            </Badge>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl border border-white/8 bg-white/3 px-4 py-3">
              <div className="flex items-center gap-2">
                <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                  Control source
                </p>
                <InfoTip
                  label="Control source"
                  content="Shows where the current autonomy settings came from, for example a database override or a runtime fallback."
                  position="right"
                />
              </div>
              <p className="mt-1 text-sm font-semibold text-cyan-200">
                {controlDraft?.source ?? "loading"}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                {controlDraft?.updated_at ?? "Not saved yet"}
                {controlDraft?.updated_by ? ` · ${controlDraft.updated_by}` : ""}
              </p>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/3 px-4 py-3">
              <div className="flex items-center gap-2">
                <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                  Effective path
                </p>
                <InfoTip
                  label="Effective path"
                  content="Explains which runtime rule currently wins. This tells you whether FAIM is using manual mode, after-upload compatibility, periodic worker mode, or hybrid automation."
                  position="right"
                />
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-100">
                {evolveStatus?.guardrails?.automation_label ?? "Loading"}
              </p>
              <p className="mt-1 text-xs text-slate-400 font-mono">
                {evolveStatus?.guardrails?.automation_path ?? "…"}
              </p>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/3 px-4 py-3">
              <div className="flex items-center gap-2">
                <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                  Execution layer
                </p>
                <InfoTip
                  label="Execution layer"
                  content="Shows whether automation is actually allowed to run through the approved worker or scheduler path."
                  position="left"
                />
              </div>
              <p className="mt-1 text-sm font-semibold text-slate-100">
                {evolveStatus?.guardrails?.jobs_enabled ? "Worker enabled" : "Worker disabled"}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                FAIM uses the approved scheduler/worker path when autonomy is on.
              </p>
            </div>
          </div>
        </div>

        <div className="grid gap-4 px-5 py-5 xl:grid-cols-[1.45fr_1fr]">
          <div className="rounded-3xl border border-white/6 bg-black/20 p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                    Editable controls
                  </p>
                  <InfoTip
                    label="Editable controls"
                    content="These buttons change what FAIM is allowed to do. They do not just change the visual state, they update the graph-scoped autonomy settings stored in FAIM."
                    position="right"
                  />
                </div>
                <p className="mt-1 text-sm text-slate-300">
                  Turn the graph autonomy on, then choose when it may run and
                  whether it can invent new structure.
                </p>
              </div>
              <Badge variant={controlDraft?.can_edit ? "success" : "outline"} size="md">
                {controlDraft?.can_edit ? "editable" : "locked"}
              </Badge>
            </div>

            {controlDraft ? (
              <div className="mt-5 grid gap-4">
                <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                          Self evolve
                        </p>
                        <InfoTip
                          label="Self evolve"
                          content="Master switch for graph autonomy. Off means the evolve worker will not auto-run for this graph."
                          position="right"
                        />
                      </div>
                      <p className="mt-1 text-sm text-slate-300">
                        Master switch for autonomy on this graph.
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant={modeChipVariant(controlDraft.self_evolve_enabled)}
                      onClick={() =>
                        void updateEvolveControl({
                          self_evolve_enabled: !controlDraft.self_evolve_enabled,
                        })
                      }
                      disabled={controlSaving || !controlDraft.can_edit}
                    >
                      {controlDraft.self_evolve_enabled ? "Enabled" : "Disabled"}
                    </Button>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                    <div className="flex items-center gap-2">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                        Trigger mode
                      </p>
                      <InfoTip
                        label="Trigger mode"
                        content="Controls when evolution is allowed to run: manual only, after uploads, on a schedule, or both."
                        position="right"
                      />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {[
                        ["manual", "Manual"],
                        ["post_upload", "After upload"],
                        ["periodic", "Periodic"],
                        ["hybrid", "Hybrid"],
                      ].map(([value, label]) => {
                        const active = controlDraft.self_evolve_trigger_mode === value;
                        return (
                          <Button
                            key={value}
                            size="sm"
                            variant={modeChipVariant(active)}
                            onClick={() =>
                              void updateEvolveControl({
                                self_evolve_trigger_mode: value,
                              })
                            }
                            disabled={controlSaving || !controlDraft.can_edit}
                          >
                            {label}
                          </Button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                    <div className="flex items-center gap-2">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                        Self invent
                      </p>
                      <InfoTip
                        label="Self invent"
                        content="Controls whether FAIM may invent new structure from graph changes now, after uploads, or both."
                        position="left"
                      />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {[
                        ["off", "Off"],
                        ["on_evolve", "On evolve"],
                        ["after_upload", "After upload"],
                        ["both", "Both"],
                      ].map(([value, label]) => {
                        const invented = normalizeInventState(
                          value as "off" | "on_evolve" | "after_upload" | "both",
                        );
                        const active =
                          controlDraft.self_invent_enabled ===
                            invented.self_invent_enabled &&
                          controlDraft.self_invent_on_evolve ===
                            invented.self_invent_on_evolve &&
                          controlDraft.self_invent_after_upload ===
                            invented.self_invent_after_upload;
                        return (
                          <Button
                            key={value}
                            size="sm"
                            variant={modeChipVariant(active)}
                            onClick={() =>
                              void updateEvolveControl({
                                ...invented,
                              })
                            }
                            disabled={controlSaving || !controlDraft.can_edit}
                          >
                            {label}
                          </Button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-white/6 bg-gradient-to-r from-cyan-500/8 via-sky-500/5 to-indigo-500/8 p-4">
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                    Saved control
                  </p>
                  <p className="mt-1 text-sm font-semibold text-cyan-200">
                    Stored in FAIM, not the browser
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    {controlSaving
                      ? "Saving changes..."
                      : "Changes update the graph-scoped control row and immediately affect the effective state."}
                  </p>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-400">
                Loading autonomy controls...
              </p>
            )}
          </div>

          <div className="rounded-3xl border border-white/6 bg-black/20 p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                    Effective state
                  </p>
                  <InfoTip
                    label="Effective state"
                    content="This is the real runtime result after the UI setting, backend guardrails, and worker availability are all combined."
                    position="left"
                  />
                </div>
                <p className="mt-1 text-sm text-slate-300">
                  What FAIM is actually allowed to do right now.
                </p>
              </div>
              <Badge
                variant={guardrailBadgeVariant(evolveStatus?.guardrails)}
                size="md"
              >
                {evolveStatus?.guardrails
                  ? evolveStatus.guardrails.automation_enabled
                    ? "active"
                    : "inactive"
                  : "loading"}
              </Badge>
            </div>

            {evolveStatus?.guardrails ? (
              <div className="mt-5 grid gap-3">
                <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                    State summary
                  </p>
                  <p className="mt-1 text-base font-semibold text-slate-100">
                    {evolveStatus.guardrails.automation_label}
                  </p>
                  <p className="mt-1 text-xs text-slate-400 font-mono">
                    {evolveStatus.guardrails.automation_path}
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                      Self evolve
                    </p>
                    <p className="mt-1 text-sm font-semibold text-slate-100">
                      {evolveStatus.guardrails.self_evolve_enabled
                        ? "enabled"
                        : "disabled"}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      Trigger mode:{" "}
                      <span className="font-mono text-slate-300">
                        {evolveStatus.guardrails.trigger_mode}
                      </span>
                    </p>
                  </div>

                  <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                      Self invent
                    </p>
                    <p className="mt-1 text-sm font-semibold text-slate-100">
                      {evolveStatus.guardrails.self_invent_enabled
                        ? "enabled"
                        : "disabled"}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      On evolve:{" "}
                      {evolveStatus.guardrails.self_invent_on_evolve
                        ? "yes"
                        : "no"}{" "}
                      | After upload:{" "}
                      {evolveStatus.guardrails.self_invent_after_upload
                        ? "yes"
                        : "no"}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                      Worker engine
                    </p>
                    <p className="mt-1 text-sm font-semibold text-slate-100">
                      {evolveStatus.guardrails.jobs_enabled
                        ? "enabled"
                        : "disabled"}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      Automation runs through the approved scheduler/worker
                      path.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                      Guardrail reason
                    </p>
                    <p className="mt-1 text-sm text-slate-100">
                      {humanizeDueReason(
                        evolveStatus.guardrails.guardrail_reason,
                      )}
                    </p>
                    <p className="mt-1 text-xs text-slate-400 font-mono">
                      {evolveStatus.guardrails.guardrail_reason}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-400">
                Loading effective state...
              </p>
            )}
          </div>
        </div>
      </div>

      {/* --- Metrics Scorecard (Storage Parity) --- */}
      <div className="relative grid grid-cols-1 overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] sm:grid-cols-2 xl:grid-cols-4">
        <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-emerald-500/80 via-emerald-400/40 to-transparent rounded-full" />
        {[
          {
            label: "Fractal D",
            value: formatMetric(metrics?.dimension_D),
            icon: Activity,
          },
          {
            label: "Entropy H",
            value: formatMetric(metrics?.entropy_H),
            icon: GitMerge,
          },
          {
            label: "Pressure λ",
            value: formatMetric(metrics?.pressure_lambda),
            icon: RefreshCw,
          },
          {
            label: "Node / Edge",
            value: `${formatCount(metrics?.node_count)} / ${formatCount(metrics?.edge_count)}`,
            icon: Hash,
          },
        ].map((stat, i) => (
          <div
            key={stat.label}
            className={`relative flex flex-col justify-center px-6 py-4 ${
              i > 0 ? "border-t sm:border-t-0 sm:border-l border-white/6" : ""
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                {stat.label}
              </p>
              <stat.icon size={18} className="opacity-20 text-cyan-300" />
            </div>
            <p
              className="font-semibold tabular-nums leading-none text-cyan-200"
              style={{ fontSize: 26 }}
            >
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-5">
        <div className="relative lg:col-span-3 flex flex-col h-[600px] lg:h-[850px] overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] !overflow-visible">
          <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-cyan-500/80 via-cyan-400/40 to-transparent rounded-full" />
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/6 px-5 py-2.5">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Evolution Timeline
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Latest graph events and evolve/invention actions
              </p>
            </div>
            <Badge variant="outline" size="sm">
              {visibleTimeline.length} items
            </Badge>
          </div>
          <div className="pt-0 px-0 flex-1 min-h-0 flex flex-col">
            {visibleTimeline.length === 0 ? (
              <p className="text-sm text-slate-500 italic px-5 py-4">
                No events available yet.
              </p>
            ) : (
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                {visibleTimeline.map((event) => (
                  <div
                    key={event.seq}
                    className="group px-5 py-4 transition-all hover:bg-white/[0.02] border-b border-white/6"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={eventBadgeVariant(event.kind)} size="sm">
                        {event.kind}
                      </Badge>
                      <Badge variant="outline" size="xs">
                        seq {event.seq}
                      </Badge>
                      <span className="text-[10px] text-slate-500 font-mono tracking-tighter">
                        {formatTimestamp(event.ts)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-200">
                      {eventSummary(event)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4 lg:col-span-2 flex flex-col h-[600px] lg:h-[850px] overflow-y-auto custom-scrollbar pr-1 pb-4">
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] shrink-0">
            <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-cyan-500/80 via-cyan-400/40 to-transparent rounded-full" />
            <div className="border-b border-white/6 px-5 py-2.5">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Latest Run Outcome
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Result from manual evolve action
              </p>
            </div>
            <div className="space-y-3 pt-4 px-5 pb-5">
              {!lastRun ? (
                <p className="text-sm text-slate-400 font-medium">
                  No manual evolve run in this session yet.
                </p>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        lastRun.status === "completed" ? "success" : "warning"
                      }
                      size="sm"
                    >
                      {lastRun.status}
                    </Badge>
                    <span className="text-xs text-slate-400">
                      v{lastRun.graph_version}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                      <p className="text-slate-400 text-xs">Merges</p>
                      <p className="font-semibold text-cyan-200">
                        {lastRun.merges}
                      </p>
                    </div>
                    <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                      <p className="text-slate-400 text-xs">Prunes</p>
                      <p className="font-semibold text-cyan-200">
                        {lastRun.prunes}
                      </p>
                    </div>
                    <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                      <p className="text-slate-400 text-xs">Inventions</p>
                      <p className="font-semibold text-cyan-200">
                        {lastRun.inventions}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400">
                    Latency: {lastRun.latency_ms} ms
                  </p>
                  <p className="text-xs text-cyan-200">
                    {buildEffectiveModeText(
                      lastRun.requested_profile,
                      lastRun.requested_persist_mode,
                      lastRun.effective_profile,
                      lastRun.effective_persist_mode,
                      lastRun.durability_path,
                    )}
                  </p>
                  <p className="text-xs text-slate-400">
                    completion: {lastRun.completion_mode || "-"} |
                    aggressiveness: {lastRun.evolve_aggressiveness || "-"} |
                    state update: {lastRun.state_update_status || "-"}
                  </p>
                </>
              )}
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] shrink-0">
            <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-purple-500/80 via-purple-400/40 to-transparent rounded-full" />
            <div className="border-b border-white/6 px-5 py-2.5">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Runtime Snapshot
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Live diagnostics and event stream health
              </p>
            </div>
            <div className="space-y-3 pt-4 px-5 pb-5 text-sm">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-slate-300">
                  <Hash size={14} className="text-cyan-300" />
                  Graph hash
                </span>
                <span className="font-mono text-xs text-slate-300">
                  {shortHash(metrics?.graph_hash)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-slate-300">
                  <Clock3 size={14} className="text-cyan-300" />
                  Last diagnostics
                </span>
                <span className="text-xs text-slate-300">
                  {formatTimestamp(metrics?.computed_at)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-slate-300">
                  <Activity size={14} className="text-cyan-300" />
                  Last seq / kind
                </span>
                <span className="text-xs text-slate-300">
                  {evolveStatus?.last_event?.last_event_seq ??
                    latest?.last_seq ??
                    0}{" "}
                  /{" "}
                  {evolveStatus?.last_event?.last_event_kind ||
                    latest?.last_kind ||
                    "-"}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-1">
                <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                  <p className="text-[11px] text-slate-400">Complete</p>
                  <p className="font-semibold text-emerald-400">
                    {eventStats.completed}
                  </p>
                </div>
                <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                  <p className="text-[11px] text-slate-400">Skipped</p>
                  <p className="font-semibold text-amber-400">
                    {eventStats.skipped}
                  </p>
                </div>
                <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                  <p className="text-[11px] text-slate-400">Invention</p>
                  <p className="font-semibold text-violet-400">
                    {eventStats.inventionSummary}
                  </p>
                </div>
              </div>

              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <p className="text-xs text-slate-400">Latest evolve event</p>
                {latestEvolutionEvent ? (
                  <>
                    <p className="mt-1 text-sm text-slate-200">
                      {eventSummary(latestEvolutionEvent)}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {formatTimestamp(latestEvolutionEvent.ts)}
                    </p>
                  </>
                ) : (
                  <p className="mt-1 text-sm text-slate-400">
                    No evolve completion/skip event yet.
                  </p>
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
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] shrink-0">
            <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-amber-500/80 via-amber-400/40 to-transparent rounded-full" />
            <div className="border-b border-white/6 px-5 py-2.5">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Scheduler State
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Step B runtime flags, due reason, and evolve job state
              </p>
            </div>
            <div className="space-y-3 pt-4 px-5 pb-5 text-sm">
              {!evolveStatus ? (
                <p className="text-sm text-slate-400">
                  Loading scheduler state...
                </p>
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
                    <Badge
                      variant={
                        evolveStatus.runtime.jobs_enabled
                          ? "success"
                          : "warning"
                      }
                      size="xs"
                    >
                      {evolveStatus.runtime.jobs_enabled
                        ? "enabled"
                        : "disabled"}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Self evolve / invent</span>
                    <span className="text-xs text-slate-200">
                      {evolveStatus.runtime.self_evolve_enabled ? "on" : "off"}{" "}
                      /{" "}
                      {evolveStatus.runtime.self_invent_enabled ? "on" : "off"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Due now</span>
                    <Badge
                      variant={evolveStatus.due.is_due ? "success" : "outline"}
                      size="xs"
                    >
                      {evolveStatus.due.is_due ? "yes" : "no"}
                    </Badge>
                  </div>
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                    <p className="text-xs text-slate-400">Due reason</p>
                    <p className="mt-1 text-xs text-slate-200">
                      {humanizeDueReason(evolveStatus.due.reason)}
                    </p>
                    <p className="mt-1 font-mono text-[11px] text-slate-500">
                      {evolveStatus.due.reason}
                    </p>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Version delta</span>
                    <span className="text-xs text-slate-200">
                      {evolveStatus.due.version_delta} /{" "}
                      {evolveStatus.due.min_version_delta}
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
                      Last skip reason:{" "}
                      {evolveStatus.last_event.last_skip_reason}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] shrink-0">
            <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-emerald-500/80 via-emerald-400/40 to-transparent rounded-full" />
            <div className="border-b border-white/6 px-5 py-2.5">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Metric Details
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Additional scorecard fields
              </p>
            </div>
            <div className="space-y-2 pt-4 px-5 pb-5 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Redundancy</span>
                <span className="text-slate-200">
                  {formatMetric(metrics?.redundancy)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Novelty</span>
                <span className="text-slate-200">
                  {formatMetric(metrics?.novelty)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-2 text-slate-400">
                  <Scissors size={13} className="text-cyan-300" />
                  Energy
                </span>
                <span className="text-slate-200">
                  {formatMetric(metrics?.energy)}
                </span>
              </div>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] shrink-0">
            <div className="absolute top-0 left-6 right-6 h-[2px] bg-gradient-to-r from-indigo-500/80 via-indigo-400/40 to-transparent rounded-full" />
            <div className="border-b border-white/6 px-5 py-3">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Source Coverage
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Latest ingested files for this graph
              </p>
            </div>
            <div className="space-y-3 pt-4 px-5 pb-5 text-sm">
              {!storageSummary ? (
                <p className="text-sm text-slate-400">
                  Loading source coverage...
                </p>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Files</span>
                    <span className="text-slate-200">
                      {formatCount(storageSummary.total_files)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Total bytes</span>
                    <span className="text-slate-200">
                      {formatBytes(storageSummary.total_bytes)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Ingested</span>
                    <span className="text-slate-200">
                      {formatCount(storageSummary.by_status?.ingested ?? 0)}
                    </span>
                  </div>
                </>
              )}
              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                <p className="text-xs text-slate-400">Latest files</p>
                {storageFiles.length === 0 ? (
                  <p className="mt-1 text-xs text-slate-400">
                    No files indexed for this graph.
                  </p>
                ) : (
                  <div className="mt-2 max-h-40 space-y-2 overflow-y-auto pr-1">
                    {storageFiles.map((file) => (
                      <div
                        key={file.raw_id}
                        className="flex items-center justify-between gap-2 rounded-lg border border-white/8 bg-white/[0.02] px-2.5 py-1.5"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-xs text-slate-200">
                            {file.filename}
                          </p>
                          <p className="text-[11px] text-slate-400">
                            nodes {file.node_count} | vectors{" "}
                            {file.vector_count}
                          </p>
                        </div>
                        <Badge
                          variant={
                            file.ingest_status === "ingested"
                              ? "success"
                              : "outline"
                          }
                          size="xs"
                        >
                          {file.ingest_status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
