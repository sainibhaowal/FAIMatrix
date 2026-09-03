"use client";

import {
  Activity,
  AlertTriangle,
  BookOpen,
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
import { EvolutionPhysicsChart } from "@/components/evolution/EvolutionPhysicsChart";
import { EvolutionManual } from "@/components/evolution/EvolutionManual";
import { InventionFlowCanvas } from "@/components/evolution/InventionFlowCanvas";
import { EvolutionVersionHistory } from "@/components/evolution/EvolutionVersionHistory";
import type {
  InventionVersionsData,
} from "@/components/evolution/EvolutionVersionHistory";
import type {
  FlowNodeData,
  InventionFlowData,
} from "@/components/evolution/InventionFlowCanvas";

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

type RawInventionFlowNode = {
  id: string;
  stage: "atom" | "macro" | "merge";
  title: string;
  subtitle: string;
  cognitive_type?: string | null;
  pressure_lambda?: number | null;
  child_count?: number | null;
  status?: string | null;
  children_details?: Array<{
    id: string;
    label: string;
    type: string;
    similarity: number;
  }> | null;
};

type RawInventionFlowResponse = {
  graph_id: string;
  tenant_id: string;
  node_count: number;
  macro_count: number;
  merge_count: number;
  stages: {
    atoms: RawInventionFlowNode[];
    macros: RawInventionFlowNode[];
    merges: RawInventionFlowNode[];
  };
  computed_at: string;
};

const VALID_COGNITIVE_TYPES = new Set([
  "fact",
  "procedure",
  "event",
  "contradiction",
  "work",
]);

type LearningKnobSamples = {
  visits: Record<string, number>;
  mean_reward: Record<string, number>;
};

type LearningStateResponse = {
  graph_id: string;
  enabled: boolean;
  schema_tag: string | null;
  policy_version: number;
  source: string;
  learned: boolean;
  knobs: Record<string, number | boolean | string>;
  calibration: { n: number; mean: number; m2: number };
  samples: Record<string, LearningKnobSamples>;
  meta: Record<string, unknown>;
  defaults: Record<string, number>;
};

type LearningOutcomeRow = {
  id: string;
  graph_id: string;
  graph_version: number;
  cycle_ts: string | null;
  merges: number;
  prunes: number;
  inventions: number;
  theories: number;
  lambda_before: number;
  lambda_after: number;
  r_before: number;
  r_after: number;
  n_before: number;
  n_after: number;
  d_before: number;
  d_after: number;
  h_before: number;
  h_after: number;
  e_before: number;
  e_after: number;
  retrieval_delta: number | null;
  reward: number;
  policy_snapshot: Record<string, unknown>;
};

type LearningOutcomesResponse = {
  graph_id: string;
  enabled: boolean;
  total: number;
  outcomes: LearningOutcomeRow[];
};

type LearningMetaRow = {
  id: string;
  graph_id: string;
  ts: string | null;
  merge_usefulness: number;
  invention_utilization: number;
  prune_regret: number;
  d_drift: number;
  h_drift: number;
  alerts: Record<string, unknown>;
  detail: Record<string, unknown>;
};

type LearningMetaResponse = {
  graph_id: string;
  enabled: boolean;
  total: number;
  meta_metrics: LearningMetaRow[];
};

function mapInventionFlowNode(
  node: RawInventionFlowNode,
): FlowNodeData {
  const cognitiveType = VALID_COGNITIVE_TYPES.has(
    (node.cognitive_type || "fact").toLowerCase(),
  )
    ? ((node.cognitive_type as string).toLowerCase() as FlowNodeData["cognitiveType"])
    : "fact";
  return {
    id: node.id,
    stage: node.stage,
    title: node.title || `Node ${node.id.slice(0, 8)}`,
    subtitle: node.subtitle || "",
    cognitiveType,
    pressureLambda:
      typeof node.pressure_lambda === "number" ? node.pressure_lambda : undefined,
    childCount:
      typeof node.child_count === "number" ? node.child_count : undefined,
    status: (node.status as FlowNodeData["status"]) || undefined,
    childrenDetails: node.children_details
      ? node.children_details.map((child) => ({
          id: child.id,
          label: child.label,
          type: child.type,
          similarity: child.similarity,
        }))
      : undefined,
  };
}

function mapInventionFlowResponse(
  raw: RawInventionFlowResponse,
): InventionFlowData {
  return {
    graph_id: raw.graph_id,
    node_count: raw.node_count,
    macro_count: raw.macro_count,
    merge_count: raw.merge_count,
    stages: {
      atoms: raw.stages.atoms.map(mapInventionFlowNode),
      macros: raw.stages.macros.map(mapInventionFlowNode),
      merges: raw.stages.merges.map(mapInventionFlowNode),
    },
    computed_at: raw.computed_at,
  };
}

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
  "EVOLUTION_ERROR",
  "EVOLUTION_PERSISTENCE_APPLIED",
  "EVOLUTION_SKIPPED",
  "EVOLUTION_MERGE",
  "PRUNE_NODE",
  "EVOLUTION_INVENTION_SUMMARY",
  "EVOLUTION_INVENTION_ERROR",
  "INVENT_MACRO_NODE",
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
  if (text === "jobs_disabled")
    return "Background job processing is disabled (FAIM_ENABLE_JOBS off).";
  if (text === "version_delta_met")
    return "Graph version delta met — due conditions satisfied.";
  if (text === "insufficient_nodes")
    return "Skipped: fewer than 2 nodes in the graph.";
  if (text === "no_actions_after_evaluation")
    return "Skipped: no merge/prune/invention actions were needed.";
  if (text.startsWith("trigger_mode_not_write_triggered:")) {
    const mode = text.split(":")[1] || "unknown";
    return `Automation does not run after uploads in "${mode}" trigger mode.`;
  }
  if (text.startsWith("trigger_mode_not_periodic:")) {
    const mode = text.split(":")[1] || "unknown";
    return `Automation does not run on a schedule in "${mode}" trigger mode.`;
  }
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
  if (kind === "EVOLUTION_ERROR") return "error";
  if (kind === "EVOLUTION_INVENTION_ERROR") return "error";
  if (kind === "EVOLUTION_INVENTION_SUMMARY") return "secondary";
  if (kind === "INVENT_MACRO_NODE") return "primary";
  if (kind === "EVOLUTION_START") return "info";
  if (kind === "EVOLUTION_PERSISTENCE_APPLIED") return "info";
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

  if (event.kind === "EVOLUTION_ERROR") {
    const text =
      typeof payload.error === "string" ? payload.error : "Evolution failed";
    return `Error: ${text}`;
  }

  if (event.kind === "INVENT_MACRO_NODE") {
    const macroId =
      typeof payload.macro_id === "string" ? shortHash(payload.macro_id) : "-";
    const members = Array.isArray(payload.member_ids)
      ? payload.member_ids.length
      : 0;
    const lambda =
      typeof payload.lambda_hat === "number"
        ? payload.lambda_hat.toFixed(3)
        : "-";
    return `Macro invented: ${macroId} from ${members} members (λ=${lambda})`;
  }

  if (event.kind === "EVOLUTION_START") {
    return `Started: ${resolveEventModeText(payload)}`.replace(
      "Started:  |",
      "Started:",
    );
  }

  if (event.kind === "EVOLUTION_PERSISTENCE_APPLIED") {
    const state = asString(payload.state_update_status) ?? "applied";
    return `Persistence applied (${state})${resolveEventModeText(payload)}`;
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

export type EvolutionPane = "controls" | "visuals" | "timeline";

const EVOLUTION_PANES: Array<{
  key: EvolutionPane;
  label: string;
  hint: string;
  accent: string;
  icon: typeof Dna;
}> = [
  {
    key: "controls",
    label: "Overview & Controls",
    hint: "CONFIG & POLICY",
    accent: "#38bdf8", // Sky-400
    icon: Dna,
  },
  {
    key: "visuals",
    label: "Physics & Topology",
    hint: "REALTIME STREAM",
    accent: "#c084fc", // Purple-400
    icon: Activity,
  },
  {
    key: "timeline",
    label: "Timeline & Logs",
    hint: "EVENT HISTORY",
    accent: "#34d399", // Emerald-400
    icon: Clock3,
  },
];

export type VisualSubTab = "spatial3d" | "physics";

export default function EvolutionPage() {
  const { data: session } = useSession();
  const { toast } = useToast();
  const [activePane, setActivePane] = useState<EvolutionPane>("controls");
  const [visualSubTab, setVisualSubTab] = useState<VisualSubTab>("spatial3d");

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
  const [flowData, setFlowData] = useState<InventionFlowData | null>(null);
  const [flowLoading, setFlowLoading] = useState(true);
  const [flowError, setFlowError] = useState<string | null>(null);
  const [versionsData, setVersionsData] =
    useState<InventionVersionsData | null>(null);
  const [versionsLoading, setVersionsLoading] = useState(true);
  const [versionsError, setVersionsError] = useState<string | null>(null);
  const [restoringVersion, setRestoringVersion] = useState<number | null>(
    null,
  );
  const [learningState, setLearningState] =
    useState<LearningStateResponse | null>(null);
  const [learningOutcomes, setLearningOutcomes] = useState<LearningOutcomeRow[]>(
    [],
  );
  const [learningMeta, setLearningMeta] = useState<LearningMetaRow[]>([]);
  const [learningLoading, setLearningLoading] = useState(true);
  const [learningError, setLearningError] = useState<string | null>(null);
  const [selfInventOnRun, setSelfInventOnRun] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState<GraphEvent[]>([]);
  const [lastRun, setLastRun] = useState<EvolveResponse | null>(null);
  const [lastSeq, setLastSeq] = useState(0);

  const [loadingSnapshot, setLoadingSnapshot] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [controlSaving, setControlSaving] = useState(false);
  const [liveStatus, setLiveStatus] = useState<LiveStatus>("idle");
  const [manualOpen, setManualOpen] = useState(false);

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showEvolutionOnly, setShowEvolutionOnly] = useState(true);
  const [pollError, setPollError] = useState<string | null>(null);

  const initializedRef = useRef(false);
  const pollBusyRef = useRef(false);
  const lastSeqRef = useRef(0);
  const pollTickRef = useRef(0);

  const selfEvolveActive = Boolean(
    controlDraft?.self_evolve_enabled ?? evolveStatus?.control?.self_evolve_enabled,
  );
  const selfInventActive = Boolean(
    controlDraft?.self_invent_enabled ?? evolveStatus?.control?.self_invent_enabled,
  );
  const controlCanEdit = Boolean(
    controlDraft?.can_edit ?? evolveStatus?.control?.can_edit,
  );

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

  const fetchInventionFlow = useCallback(
    async (targetGraphId: string): Promise<InventionFlowData> => {
      const params = new URLSearchParams({ graph_id: targetGraphId });
      const raw = await apiRequest<RawInventionFlowResponse>(
        `/api/v1/evolve/invention/flow?${params.toString()}`,
      );
      return mapInventionFlowResponse(raw);
    },
    [],
  );

  const fetchInventionVersions = useCallback(
    async (targetGraphId: string): Promise<InventionVersionsData> => {
      const params = new URLSearchParams({ graph_id: targetGraphId });
      return apiRequest<InventionVersionsData>(
        `/api/v1/evolve/invention/versions?${params.toString()}`,
      );
    },
    [],
  );

  const fetchLearningState = useCallback(
    async (targetGraphId: string): Promise<LearningStateResponse> => {
      const params = new URLSearchParams({ graph_id: targetGraphId });
      return apiRequest<LearningStateResponse>(
        `/api/v1/evolve/learning/state?${params.toString()}`,
      );
    },
    [],
  );

  const fetchLearningOutcomes = useCallback(
    async (targetGraphId: string): Promise<LearningOutcomesResponse> => {
      const params = new URLSearchParams({ graph_id: targetGraphId });
      return apiRequest<LearningOutcomesResponse>(
        `/api/v1/evolve/learning/outcomes?${params.toString()}`,
      );
    },
    [],
  );

  const fetchLearningMeta = useCallback(
    async (targetGraphId: string): Promise<LearningMetaResponse> => {
      const params = new URLSearchParams({ graph_id: targetGraphId });
      return apiRequest<LearningMetaResponse>(
        `/api/v1/evolve/learning/meta?${params.toString()}`,
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

        try {
          const flow = await fetchInventionFlow(targetGraphId);
          setFlowData(flow);
          setFlowError(null);
        } catch (flowErr) {
          const message =
            flowErr instanceof Error
              ? flowErr.message
              : "Invention flow unavailable";
          setFlowError(message);
        } finally {
          setFlowLoading(false);
        }

        try {
          const versions = await fetchInventionVersions(targetGraphId);
          setVersionsData(versions);
          setVersionsError(null);
        } catch (versionsErr) {
          const message =
            versionsErr instanceof Error
              ? versionsErr.message
              : "Version history unavailable";
          setVersionsError(message);
        } finally {
          setVersionsLoading(false);
        }

        try {
          const [stateData, outcomesData, metaData] = await Promise.all([
            fetchLearningState(targetGraphId),
            fetchLearningOutcomes(targetGraphId),
            fetchLearningMeta(targetGraphId),
          ]);
          setLearningState(stateData);
          setLearningOutcomes(outcomesData.outcomes || []);
          setLearningMeta(metaData.meta_metrics || []);
          setLearningError(null);
        } catch (learningErr) {
          const message =
            learningErr instanceof Error
              ? learningErr.message
              : "Learning state unavailable";
          setLearningError(message);
        } finally {
          setLearningLoading(false);
        }
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
      fetchInventionFlow,
      fetchInventionVersions,
      fetchLatest,
      fetchLearningMeta,
      fetchLearningOutcomes,
      fetchLearningState,
      fetchScorecard,
      fetchStorageFiles,
      fetchStorageSummary,
      toast,
    ],
  );

  const reloadLearning = useCallback(
    async (targetGraphId: string) => {
      setLearningLoading(true);
      setLearningError(null);
      try {
        const [stateData, outcomesData, metaData] = await Promise.all([
          fetchLearningState(targetGraphId),
          fetchLearningOutcomes(targetGraphId),
          fetchLearningMeta(targetGraphId),
        ]);
        setLearningState(stateData);
        setLearningOutcomes(outcomesData.outcomes || []);
        setLearningMeta(metaData.meta_metrics || []);
      } catch (learningErr) {
        const message =
          learningErr instanceof Error
            ? learningErr.message
            : "Learning state unavailable";
        setLearningError(message);
      } finally {
        setLearningLoading(false);
      }
    },
    [fetchLearningMeta, fetchLearningOutcomes, fetchLearningState],
  );

  const reloadFlow = useCallback(
    async (targetGraphId: string) => {
      setFlowLoading(true);
      setFlowError(null);
      try {
        const flow = await fetchInventionFlow(targetGraphId);
        setFlowData(flow);
      } catch (flowErr) {
        const message =
          flowErr instanceof Error
            ? flowErr.message
            : "Invention flow unavailable";
        setFlowError(message);
      } finally {
        setFlowLoading(false);
      }
    },
    [fetchInventionFlow],
  );

  const reloadVersions = useCallback(
    async (targetGraphId: string) => {
      setVersionsLoading(true);
      setVersionsError(null);
      try {
        const versions = await fetchInventionVersions(targetGraphId);
        setVersionsData(versions);
      } catch (versionsErr) {
        const message =
          versionsErr instanceof Error
            ? versionsErr.message
            : "Version history unavailable";
        setVersionsError(message);
      } finally {
        setVersionsLoading(false);
      }
    },
    [fetchInventionVersions],
  );

  const handleRestoreVersion = useCallback(
    async (version: number) => {
      if (!graphId) return;
      setRestoringVersion(version);
      try {
        const result = await apiRequest<{
          restored: number;
          skipped: number;
        }>("/api/v1/evolve/backups/restore", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ graph_id: graphId, version }),
        });
        toast.success(
          "Cycle restored",
          `${result.restored} node${result.restored === 1 ? "" : "s"} restored${
            result.skipped > 0
              ? `, ${result.skipped} already present (skipped)`
              : ""
          }`,
        );
        await refreshAll(graphId);
      } catch (restoreErr) {
        const message =
          restoreErr instanceof Error
            ? restoreErr.message
            : "Restore failed";
        toast.error("Restore failed", message);
      } finally {
        setRestoringVersion(null);
      }
    },
    [graphId, refreshAll, toast],
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

          try {
            const flow = await fetchInventionFlow(targetGraphId);
            setFlowData(flow);
            setFlowError(null);
          } catch (flowErr) {
            const message =
              flowErr instanceof Error
                ? flowErr.message
                : "Invention flow unavailable";
            setFlowError(message);
          } finally {
            setFlowLoading(false);
          }
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
      fetchInventionFlow,
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
        self_invent_requested: selfInventOnRun,
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
  }, [graphId, persistMode, profile, refreshAll, selfInventOnRun, toast]);

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
    setFlowData(null);
    setFlowError(null);
    setFlowLoading(true);
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

  const physicsPoints = useMemo(() => {
    if (evolutionEvents.length > 0) {
      return evolutionEvents.slice(-10).map((ev, idx) => {
        const payload = ev.payload || {};
        return {
          time: ev.ts
            ? new Date(ev.ts).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })
            : `Seq ${ev.seq}`,
          seq: ev.seq,
          entropy:
            typeof payload.H_hat === "number"
              ? payload.H_hat
              : typeof payload.entropy === "number"
                ? payload.entropy
                : metrics?.entropy_H ?? 0.45,
          redundancy:
            typeof payload.redundancy_R === "number"
              ? payload.redundancy_R
              : typeof payload.redundancy === "number"
                ? payload.redundancy
                : metrics?.redundancy ?? 0.15,
          novelty:
            typeof payload.novelty_N === "number"
              ? payload.novelty_N
              : typeof payload.novelty === "number"
                ? payload.novelty
                : metrics?.novelty ?? 0.85,
          pressure:
            typeof payload.lambda_hat === "number"
              ? payload.lambda_hat
              : typeof payload.pressure_lambda === "number"
                ? payload.pressure_lambda
                : metrics?.pressure_lambda ?? 0.2,
          energy:
            typeof payload.energy_E === "number"
              ? payload.energy_E
              : typeof payload.energy === "number"
                ? payload.energy
                : metrics?.energy ?? 0.95,
        };
      });
    }

    // Fallback: construct live points from active metrics scorecard
    const H = metrics?.entropy_H ?? 0.42;
    const R = metrics?.redundancy ?? 0.14;
    const N = metrics?.novelty ?? 0.86;
    const Lambda = metrics?.pressure_lambda ?? 0.18;
    const E = metrics?.energy ?? 0.92;

    return [
      { time: "T-4", entropy: Math.max(0, H - 0.1), redundancy: Math.max(0, R + 0.08), novelty: Math.min(1, N - 0.05), pressure: Math.max(0, Lambda + 0.1), energy: Math.max(0, E - 0.05) },
      { time: "T-3", entropy: Math.max(0, H - 0.05), redundancy: Math.max(0, R + 0.05), novelty: Math.min(1, N - 0.03), pressure: Math.max(0, Lambda + 0.05), energy: Math.max(0, E - 0.02) },
      { time: "T-2", entropy: H, redundancy: Math.max(0, R + 0.02), novelty: N, pressure: Lambda, energy: E },
      { time: "T-1", entropy: Math.max(0, H - 0.02), redundancy: R, novelty: Math.min(1, N + 0.02), pressure: Math.max(0, Lambda - 0.02), energy: E },
      { time: "Now", entropy: H, redundancy: R, novelty: N, pressure: Lambda, energy: E },
    ];
  }, [evolutionEvents, metrics]);

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
        subtitle={`Real-time graph metrics, autonomous evolve dynamics, and self-invention stream for graph ${graphId}`}
        icon={Dna}
        titleTestId="evolution-page-title"
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => setManualOpen(true)}>
              <BookOpen size={13} className="text-fuchsia-300" />
              User Manual
            </Button>
            <Badge variant={liveStatusVariant(liveStatus)} size="md">
              {liveStatus === "refreshing"
                ? "Live Syncing"
                : liveStatus === "live"
                  ? "Real-time Live"
                  : liveStatus === "error"
                    ? "Error"
                    : "Live"}
            </Badge>
          </div>
        }
      />
      <EvolutionManual open={manualOpen} onClose={() => setManualOpen(false)} />
      {/* Top Pane Navigation Bar (Domain Studio Aesthetics) */}
      <div className="sticky top-3 z-30 mx-auto flex max-w-[1480px] justify-center px-2">
        <div className="flex flex-wrap items-center gap-2.5 rounded-2xl border border-white/10 bg-black/60 px-3.5 py-2 shadow-[0_12px_32px_rgba(0,0,0,0.5)] backdrop-blur-xl">
          {EVOLUTION_PANES.map((pane) => {
            const active = activePane === pane.key;
            const Icon = pane.icon;
            return (
              <button
                key={pane.key}
                type="button"
                onClick={() => setActivePane(pane.key)}
                className="inline-flex items-center gap-2.5 rounded-[12px] border px-3.5 py-2 text-left transition-all duration-200 shadow-[0_10px_24px_rgba(0,0,0,0.22)]"
                style={{
                  borderColor: active ? `${pane.accent}55` : "rgba(255,255,255,0.08)",
                  backgroundColor: active ? `${pane.accent}1E` : "rgba(255,255,255,0.02)",
                  boxShadow: active ? `0 0 0 1px ${pane.accent}33` : "none",
                }}
              >
                <span
                  className="flex h-7 w-7 items-center justify-center rounded-[10px]"
                  style={{ backgroundColor: `${pane.accent}18`, color: pane.accent }}
                >
                  <Icon size={14} />
                </span>
                <span className="flex flex-col">
                  <span
                    className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em]"
                    style={{ color: active ? pane.accent : "rgba(148,163,184,0.8)" }}
                  >
                    {pane.hint}
                  </span>
                  <span className="text-[11px] font-medium text-white">{pane.label}</span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* --- PANE 1: OVERVIEW & CONTROLS --- */}
      {activePane === "controls" && (
        <div className="space-y-4">
          {/* Unified Real-Time Controls Deck */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] !overflow-visible">
            <div className="border-b border-white/6 px-5 py-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                  Graph Controls
                </p>
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  Active graph configuration and autonomous execution knobs
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={selfEvolveActive ? "success" : "outline"} size="md">
                  {selfEvolveActive ? "Self-Evolve Active" : "Self-Evolve Off"}
                </Badge>
                <Badge variant={selfInventActive ? "success" : "outline"} size="md">
                  {selfInventActive ? "Self-Invent Active" : "Self-Invent Off"}
                </Badge>
              </div>
            </div>

            <div className="p-5 grid gap-5 md:grid-cols-4">
              {/* 1. Graph Context */}
              <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3.5 flex flex-col justify-between">
                <div>
                  <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500">
                    Graph Context
                  </p>
                  <p className="mt-1 font-mono text-sm text-cyan-200">{graphId}</p>
                </div>
                <p className="mt-1 text-[11px] text-slate-400">
                  Session bound
                </p>
              </div>

              {/* 2. Profile */}
              <ThemedSelect
                label="Profile"
                options={profileOptions}
                value={profile}
                onChange={setProfile}
              />

              {/* 3. Persist Mode */}
              <ThemedSelect
                label="Persist mode"
                options={persistModeOptions}
                value={persistMode}
                onChange={setPersistMode}
              />

              {/* Mode Policy Summary */}
              <div className="rounded-[14px] border border-cyan-500/20 bg-cyan-500/5 p-3 flex flex-col justify-center text-[11px]">
                <span className="font-semibold text-cyan-200">
                  Policy: {selectedModeLabel}
                </span>
                <span className="text-slate-400 mt-0.5">
                  {getProfileHelper(profile)} {getPersistHelper(persistMode)}
                </span>
              </div>

              {/* 4. Trigger Mode */}
              <div className="md:col-span-2 relative overflow-hidden rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-sky-400/80 via-sky-400/30 to-transparent" />
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] uppercase tracking-[0.3em] font-bold text-slate-400">
                    Trigger Mode
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500">
                      Self-evolve
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        void updateEvolveControl({
                          self_evolve_enabled: !selfEvolveActive,
                        })
                      }
                      disabled={controlSaving || !controlCanEdit}
                      aria-pressed={selfEvolveActive}
                      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors ${
                        selfEvolveActive
                          ? "border-sky-400/60 bg-sky-500/40"
                          : "border-white/15 bg-white/[0.06]"
                      } disabled:opacity-40`}
                    >
                      <span
                        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                          selfEvolveActive ? "translate-x-[18px]" : "translate-x-[3px]"
                        }`}
                      />
                    </button>
                  </div>
                  <InfoTip
                    label="Trigger mode"
                    content="Controls when evolution runs: manual only, after uploads, on a schedule, or hybrid. Toggle self-evolve on to let FAIM act autonomously."
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
                    const active = (controlDraft?.self_evolve_trigger_mode ?? "manual") === value;
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
                        disabled={
                          !selfEvolveActive ||
                          controlSaving ||
                          (controlDraft ? !controlDraft.can_edit : false)
                        }
                      >
                        {label}
                      </Button>
                    );
                  })}
                </div>
              </div>

              {/* 5. Self Invent */}
              <div className="md:col-span-2 relative overflow-hidden rounded-2xl border border-white/6 bg-white/[0.03] p-4">
                <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] uppercase tracking-[0.3em] font-bold text-slate-400">
                    Self Invent Mode
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500">
                      Self-invent
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        void updateEvolveControl({
                          self_invent_enabled: !selfInventActive,
                        })
                      }
                      disabled={controlSaving || !controlCanEdit}
                      aria-pressed={selfInventActive}
                      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors ${
                        selfInventActive
                          ? "border-purple-400/60 bg-purple-500/40"
                          : "border-white/15 bg-white/[0.06]"
                      } disabled:opacity-40`}
                    >
                      <span
                        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                          selfInventActive ? "translate-x-[18px]" : "translate-x-[3px]"
                        }`}
                      />
                    </button>
                  </div>
                  <InfoTip
                    label="Self invent"
                    content="Controls whether FAIM invents new structure: off, on evolve, after upload, or both. Toggle self-invent on to allow invention."
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
                      controlDraft?.self_invent_enabled === invented.self_invent_enabled &&
                      controlDraft?.self_invent_on_evolve === invented.self_invent_on_evolve &&
                      controlDraft?.self_invent_after_upload === invented.self_invent_after_upload;
                    return (
                      <Button
                        key={value}
                        size="sm"
                        variant={modeChipVariant(active)}
                        onClick={() => void updateEvolveControl(invented)}
                        disabled={
                          !selfInventActive ||
                          controlSaving ||
                          (controlDraft ? !controlDraft.can_edit : false)
                        }
                      >
                        {label}
                      </Button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Run Evolution */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="border-b border-white/6 px-5 py-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                  Run Evolution Cycle
                </p>
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  Manually trigger merge / prune / self-invention on the active graph
                </p>
              </div>
              {lastRun && (
                <div className="flex items-center gap-2">
                  <Badge
                    variant={lastRun.status === "completed" ? "success" : "warning"}
                    size="sm"
                  >
                    {lastRun.status}
                  </Badge>
                  <span className="text-[11px] text-slate-400">
                    v{lastRun.graph_version} · {lastRun.merges} merges ·{" "}
                    {lastRun.prunes} prunes · {lastRun.inventions} inventions ·{" "}
                    {lastRun.latency_ms} ms
                  </span>
                </div>
              )}
            </div>
            <div className="p-5 flex flex-wrap items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => void runEvolve()}
                disabled={runLoading || !graphId.trim()}
                className="inline-flex items-center gap-2 rounded-xl border border-cyan-400/40 bg-cyan-500/15 px-5 py-2.5 text-sm font-semibold text-cyan-100 transition-colors hover:bg-cyan-500/25 disabled:opacity-40"
              >
                <Play size={15} className={runLoading ? "animate-pulse" : ""} />
                {runLoading ? "Running..." : "Run Evolution"}
              </button>

              <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
                <button
                  type="button"
                  role="checkbox"
                  aria-checked={selfInventOnRun}
                  onClick={() => setSelfInventOnRun((v) => !v)}
                  className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors ${
                    selfInventOnRun
                      ? "border-purple-400/60 bg-purple-500/40"
                      : "border-white/15 bg-white/[0.06]"
                  }`}
                >
                  <span
                    className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      selfInventOnRun ? "translate-x-[18px]" : "translate-x-[3px]"
                    }`}
                  />
                </button>
                <Sparkles size={13} className="text-purple-300" />
                Self-invent on this run
              </label>

              <p className="text-[11px] text-slate-500">
                Runs with {selectedModeLabel} policy
                {selfInventOnRun ? " · invention requested" : ""} for graph{" "}
                <span className="font-mono text-slate-300">{graphId}</span>
              </p>
            </div>
          </div>

          {/* Metrics Scorecard */}
          <div className="relative grid grid-cols-1 overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] sm:grid-cols-2 xl:grid-cols-4">
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

          {/* Scheduler & Metric Details Grid */}
          <div className="grid gap-4 xl:grid-cols-2">
            {/* Scheduler State Card */}
            <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
              <div className="border-b border-white/6 px-5 py-3">
                <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                  Scheduler State
                </p>
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  Runtime flags, due reason, and evolve job state
                </p>
              </div>
              <div className="space-y-3 pt-4 px-5 pb-5 text-sm">
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
                      <Badge
                        variant={evolveStatus.runtime.jobs_enabled ? "success" : "warning"}
                        size="xs"
                      >
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
                        {evolveStatus.due.version_delta} / {evolveStatus.due.min_version_delta}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Last evolved</span>
                      <span className="text-xs text-slate-200">
                        {formatTimestamp(evolveStatus.state.last_evolved_at)}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Metric Details Card */}
            <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
              <div className="border-b border-white/6 px-5 py-3">
                <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                  Metric Details
                </p>
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  Additional invariant scorecard fields
                </p>
              </div>
              <div className="space-y-3 pt-4 px-5 pb-5 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Redundancy (R)</span>
                  <span className="font-semibold text-rose-300">
                    {formatMetric(metrics?.redundancy)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Novelty (N)</span>
                  <span className="font-semibold text-emerald-300">
                    {formatMetric(metrics?.novelty)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-slate-400">
                    <Scissors size={13} className="text-cyan-300" />
                    Energy (E)
                  </span>
                  <span className="font-semibold text-purple-300">
                    {formatMetric(metrics?.energy)}
                  </span>
                </div>
                <div className="pt-2 border-t border-white/6 flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-slate-400">
                    <Hash size={13} className="text-slate-400" />
                    Graph hash
                  </span>
                  <span className="font-mono text-xs text-slate-300">
                    {shortHash(metrics?.graph_hash)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-slate-400">
                    <Clock3 size={13} className="text-slate-400" />
                    Last computed
                  </span>
                  <span className="text-xs text-slate-300">
                    {formatTimestamp(metrics?.computed_at)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Learning & Self-Optimization */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/6 px-5 py-3">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                  <span className="inline-flex items-center gap-1.5">
                    <Sparkles size={13} className="text-fuchsia-300" />
                    Learning & Self-Optimization
                  </span>
                </p>
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  LinUCB policy state, lambda calibration, outcomes & maturity metrics
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant={learningState?.enabled ? "success" : "outline"}
                  size="sm"
                >
                  {learningState?.enabled ? "learning on" : "learning off"}
                </Badge>
                {learningState?.schema_tag && (
                  <Badge variant="outline" size="xs">
                    schema {learningState.schema_tag}
                  </Badge>
                )}
                <Badge variant="outline" size="xs">
                  v{learningState?.policy_version ?? 0}
                </Badge>
                {learningState && (
                  <Badge
                    variant={learningState.learned ? "warning" : "outline"}
                    size="xs"
                  >
                    {learningState.source}
                  </Badge>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void reloadLearning(graphId)}
                  disabled={learningLoading}
                >
                  <RefreshCw
                    size={12}
                    className={learningLoading ? "animate-spin" : ""}
                  />
                  Refresh
                </Button>
              </div>
            </div>
            <div className="p-5">
              {learningError ? (
                <p className="text-sm text-rose-300">{learningError}</p>
              ) : !learningState ? (
                <p className="text-sm text-slate-400">Loading learning state...</p>
              ) : (
                <div className="grid gap-4 xl:grid-cols-3">
                  {/* Learned knobs */}
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500">
                      Learned knobs
                    </p>
                    <div className="mt-2 space-y-2">
                      {Object.entries(learningState.defaults).map(([knob, dflt]) => {
                        const value = learningState.knobs[knob];
                        const changed = typeof value === "number" && value !== dflt;
                        const visits = Object.keys(
                          learningState.samples[knob]?.visits ?? {},
                        ).length;
                        return (
                          <div
                            key={knob}
                            className="flex items-center justify-between gap-2"
                          >
                            <span className="font-mono text-[11px] text-slate-400">
                              {knob}
                            </span>
                            <span className="flex items-center gap-2">
                              {visits > 0 && (
                                <span className="font-mono text-[10px] text-slate-500">
                                  {visits} samples
                                </span>
                              )}
                              <span
                                className={`font-mono text-xs ${
                                  changed ? "text-fuchsia-300" : "text-slate-200"
                                }`}
                              >
                                {String(value)}
                              </span>
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    {learningState.meta &&
                      Object.keys(learningState.meta).length > 0 && (
                        <div className="mt-3 border-t border-white/6 pt-2">
                          <p className="text-[10px] uppercase tracking-widest text-slate-500">
                            State meta
                          </p>
                          <p className="mt-1 font-mono text-[11px] text-slate-400 break-words">
                            {Object.entries(learningState.meta).map(
                              ([key, value]) => `${key}:${String(value)}`,
                            ).join(" · ")}
                          </p>
                        </div>
                      )}
                  </div>

                  {/* Lambda calibration + visits */}
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500">
                      Lambda calibration & bandit visits
                    </p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-slate-400 text-xs">Samples</span>
                      <span className="font-mono text-xs text-slate-200">
                        {learningState.calibration.n}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 text-xs">Mean λ</span>
                      <span className="font-mono text-xs text-slate-200">
                        {learningState.calibration.mean.toFixed(4)}
                      </span>
                    </div>
                    {Object.entries(learningState.samples).map(
                      ([knob, sample]) => {
                        const entries = Object.entries(sample.visits || {});
                        if (entries.length === 0) return null;
                        return (
                          <div
                            key={knob}
                            className="mt-3 border-t border-white/6 pt-2"
                          >
                            <p className="font-mono text-[11px] text-slate-400">
                              {knob}
                            </p>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {entries.map(([value, count]) => (
                                <span
                                  key={value}
                                  className="rounded-md border border-white/8 bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-slate-300"
                                >
                                  {value}×{count}
                                </span>
                              ))}
                            </div>
                          </div>
                        );
                      },
                    )}
                  </div>

                  {/* Recent outcomes + meta metrics */}
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500">
                      Recent outcomes & maturity
                    </p>
                    {learningMeta.length > 0 && (
                      <div className="mt-2 space-y-1.5">
                        {learningMeta.slice(0, 3).map((metric) => (
                          <div
                            key={metric.id}
                            className="rounded-lg border border-white/6 bg-white/[0.02] px-2 py-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-[10px] text-slate-500">
                                {formatTimestamp(metric.ts)}
                              </span>
                              <span className="font-mono text-[10px] text-emerald-300">
                                merge {metric.merge_usefulness.toFixed(2)}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="text-slate-400">
                                invent {metric.invention_utilization.toFixed(2)}
                              </span>
                              <span className="text-slate-400">
                                regret {metric.prune_regret.toFixed(2)}
                              </span>
                              <span className="text-slate-400">
                                d-drift {metric.d_drift.toFixed(3)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {learningOutcomes.length > 0 && (
                      <div className="mt-3 border-t border-white/6 pt-2 space-y-1.5">
                        {learningOutcomes.slice(0, 4).map((row) => (
                          <div
                            key={row.id}
                            className="flex items-center justify-between rounded-lg border border-white/6 bg-white/[0.02] px-2 py-1.5"
                          >
                            <span className="font-mono text-[10px] text-slate-500">
                              v{row.graph_version}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              +{row.merges}m −{row.prunes}p +{row.inventions}i
                            </span>
                            <span className="font-mono text-[10px] text-cyan-300">
                              r={row.reward.toFixed(2)}
                            </span>
                            {row.retrieval_delta != null && (
                              <span className="font-mono text-[10px] text-fuchsia-300">
                                δ={row.retrieval_delta.toFixed(2)}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {learningMeta.length === 0 && learningOutcomes.length === 0 && (
                      <p className="mt-2 text-xs text-slate-500">
                        No outcomes recorded yet. Learning rows appear after the
                        first evolution cycle.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>

            <EvolutionVersionHistory
              data={versionsData}
              loading={versionsLoading}
              error={versionsError}
              onRetry={() => void reloadVersions(graphId)}
              onRestore={handleRestoreVersion}
              restoringVersion={restoringVersion}
            />
          </div>

          {/* Storage Section */}
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="border-b border-white/6 px-5 py-3">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Ingested Storage
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Raw file registry feeding graph memory
              </p>
            </div>
            <div className="p-5 space-y-4">
              {!storageSummary ? (
                <p className="text-sm text-slate-400">Loading storage summary...</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-4">
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500">
                      Files
                    </p>
                    <p className="mt-1 font-semibold tabular-nums text-cyan-200">
                      {formatCount(storageSummary.total_files)}
                    </p>
                  </div>
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500">
                      Total size
                    </p>
                    <p className="mt-1 font-semibold tabular-nums text-cyan-200">
                      {formatBytes(storageSummary.total_bytes)}
                    </p>
                  </div>
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500">
                      By status
                    </p>
                    <p className="mt-1 text-xs text-slate-300">
                      {Object.entries(storageSummary.by_status || {}).map(
                        ([status, count]) => `${status}:${count}`,
                      ).join(" · ") || "-"}
                    </p>
                  </div>
                  <div className="rounded-[14px] border border-white/8 bg-white/[0.03] p-3">
                    <p className="text-[10px] uppercase tracking-widest text-slate-500">
                      By type
                    </p>
                    <p className="mt-1 text-xs text-slate-300">
                      {Object.entries(storageSummary.by_type || {}).map(
                        ([type, count]) => `${type}:${count}`,
                      ).join(" · ") || "-"}
                    </p>
                  </div>
                </div>
              )}
              {storageFiles.length > 0 && (
                <div className="overflow-x-auto rounded-[14px] border border-white/8">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/8 text-[10px] uppercase tracking-widest text-slate-500">
                        <th className="px-3 py-2 font-medium">File</th>
                        <th className="px-3 py-2 font-medium">Type</th>
                        <th className="px-3 py-2 font-medium">Size</th>
                        <th className="px-3 py-2 font-medium">Status</th>
                        <th className="px-3 py-2 font-medium">Nodes / Vecs</th>
                      </tr>
                    </thead>
                    <tbody>
                      {storageFiles.slice(0, 6).map((file) => (
                        <tr
                          key={file.raw_id}
                          className="border-b border-white/4 last:border-b-0 text-slate-300"
                        >
                          <td className="px-3 py-2 font-mono max-w-[220px] truncate">
                            {file.filename}
                          </td>
                          <td className="px-3 py-2">{file.mime_type}</td>
                          <td className="px-3 py-2 tabular-nums">
                            {formatBytes(file.size_bytes)}
                          </td>
                          <td className="px-3 py-2">
                            <Badge
                              variant={
                                file.ingest_status === "ingested"
                                  ? "success"
                                  : file.ingest_status === "error"
                                    ? "error"
                                    : "outline"
                              }
                              size="xs"
                            >
                              {file.ingest_status}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 tabular-nums">
                            {file.node_count} / {file.vector_count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --- PANE 2: REAL-TIME PHYSICS & TOPOLOGY --- */}
      {activePane === "visuals" && (
        <div className="relative flex flex-col rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] p-3.5 sm:p-4 shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
          {/* Integrated Master Card Header with Floating Sub-Toggle Switcher */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3 pb-2.5 border-b border-white/6">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Self-Invention & Physics Pipeline
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                2.5D Left-to-Right Flow Diagram Canvas, Invention Inspector & Physics Stream
              </p>
            </div>

            {/* Integrated Header Sub-Toggle Switcher */}
            <div className="flex items-center gap-1.5 rounded-xl border border-white/8 bg-white/[0.03] p-1">
              {[
                ["spatial3d", "2.5D Invention Flow", Activity],
                ["physics", "Physics Stream", GitMerge],
              ].map(([key, label, Icon]: any) => {
                const active = visualSubTab === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setVisualSubTab(key as VisualSubTab)}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-mono transition-all duration-200 ${
                      active
                        ? "bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-md"
                        : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                    }`}
                  >
                    <Icon size={13} />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Master Viewport Content */}
          <div className="w-full">
            {visualSubTab === "spatial3d" && (
              <InventionFlowCanvas
                graphId={graphId}
                data={flowData}
                loading={flowLoading}
                error={flowError}
                onRetry={() => void reloadFlow(graphId)}
              />
            )}

            {visualSubTab === "physics" && (
              <div className="min-h-[440px]">
                <EvolutionPhysicsChart data={physicsPoints} />
              </div>
            )}
          </div>
        </div>
      )}

      {/* --- PANE 3: TIMELINE & EVENT LOGS --- */}
      {activePane === "timeline" && (
        <div className="grid items-start gap-4 lg:grid-cols-5">
          {/* Evolution Event Stream Timeline */}
          <div className="relative lg:col-span-3 flex flex-col h-[600px] lg:h-[750px] overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] !overflow-visible">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/6 px-5 py-3">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                  Evolution Timeline
                </p>
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  Latest graph events and evolve/invention actions
                </p>
              </div>
              <div className="flex items-center gap-4">
                <label className="flex cursor-pointer items-center gap-2 text-[11px] text-slate-400">
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={showEvolutionOnly}
                    onClick={() => setShowEvolutionOnly((v) => !v)}
                    className={`relative inline-flex h-4 w-7 shrink-0 items-center rounded-full border transition-colors ${
                      showEvolutionOnly
                        ? "border-emerald-400/60 bg-emerald-500/40"
                        : "border-white/15 bg-white/[0.06]"
                    }`}
                  >
                    <span
                      className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-transform ${
                        showEvolutionOnly ? "translate-x-[14px]" : "translate-x-[2px]"
                      }`}
                    />
                  </button>
                  Evolution-only
                </label>
                <label className="flex cursor-pointer items-center gap-2 text-[11px] text-slate-400">
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={autoRefresh}
                    onClick={() => setAutoRefresh((v) => !v)}
                    className={`relative inline-flex h-4 w-7 shrink-0 items-center rounded-full border transition-colors ${
                      autoRefresh
                        ? "border-cyan-400/60 bg-cyan-500/40"
                        : "border-white/15 bg-white/[0.06]"
                    }`}
                  >
                    <span
                      className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-transform ${
                        autoRefresh ? "translate-x-[14px]" : "translate-x-[2px]"
                      }`}
                    />
                  </button>
                  Auto-refresh ({POLL_INTERVAL_MS / 1000}s)
                </label>
                <Badge variant="outline" size="sm">
                  {visibleTimeline.length} items
                </Badge>
              </div>
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

          {/* Right Column: Run Outcome & Runtime Snapshot */}
          <div className="space-y-4 lg:col-span-2 flex flex-col h-[600px] lg:h-[750px] overflow-y-auto custom-scrollbar pr-1 pb-4">
            {/* Latest Run Outcome Card */}
            <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] shrink-0">
              <div className="border-b border-white/6 px-5 py-2.5">
                <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                  Latest Run Outcome
                </p>
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  Result from recent evolve cycle
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
                        variant={lastRun.status === "completed" ? "success" : "warning"}
                        size="sm"
                      >
                        {lastRun.status}
                      </Badge>
                      <span className="text-xs text-slate-400">
                        v{lastRun.graph_version}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
                        <p className="text-slate-400 text-xs">Merges</p>
                        <p className="font-semibold text-cyan-200">{lastRun.merges}</p>
                      </div>
                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-sky-400/80 via-sky-400/30 to-transparent" />
                        <p className="text-slate-400 text-xs">Prunes</p>
                        <p className="font-semibold text-cyan-200">{lastRun.prunes}</p>
                      </div>
                      <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                        <div className="absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-400/80 via-purple-400/30 to-transparent" />
                        <p className="text-slate-400 text-xs">Inventions</p>
                        <p className="font-semibold text-cyan-200">{lastRun.inventions}</p>
                      </div>
                    </div>
                    <p className="text-xs text-slate-400">Latency: {lastRun.latency_ms} ms</p>
                  </>
                )}
              </div>
            </div>

            {/* Runtime Snapshot Card */}
            <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)] shrink-0">
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
                <div className="grid grid-cols-3 gap-2 pt-1">
                  <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                    <p className="text-[11px] text-slate-400">Complete</p>
                    <p className="font-semibold text-emerald-400">{eventStats.completed}</p>
                  </div>
                  <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                    <p className="text-[11px] text-slate-400">Skipped</p>
                    <p className="font-semibold text-amber-400">{eventStats.skipped}</p>
                  </div>
                  <div className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-2.5">
                    <p className="text-[11px] text-slate-400">Invention</p>
                    <p className="font-semibold text-violet-400">{eventStats.inventionSummary}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
