"use client";

import {
  FileSearch,
  FileText,
  RefreshCw,
  RotateCcw,
  Search,
  UploadCloud,
  X,
  XCircle,
  ChevronDown,
  HardDrive,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Database,
  Activity,
  Key,
  Download,
  ServerCog,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { getSession, useSession } from "next-auth/react";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { GlassHeader } from "@/components/layout/GlassHeader";

import {
  Badge,
  Button,
  Card,
  Input,
  Progress,
  useToast,
} from "@/components/ui";
import {
  buildEffectiveModeText,
  formatModePair,
  getPersistHelper,
  getProfileHelper,
  resolveUiModePolicy,
} from "@/lib/profilePersistModes";

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

// --- Custom Themed Select Component ---
function ThemedSelect<T extends string>({
  value,
  onChange,
  options,
  className = "",
  placeholder = "Select...",
}: {
  value: T;
  onChange: (val: T) => void;
  options: { value: T; label: string }[];
  className?: string;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const current = options.find((o) => o.value === value);

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex h-8 w-full items-center justify-between gap-2 rounded-lg border px-2.5 text-xs outline-none transition-all hover:bg-white/5 active:scale-[0.98]"
        style={{
          background: "var(--os-surface-2)",
          borderColor: "var(--os-stroke)",
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
              className="absolute left-0 top-9 z-[var(--z-dropdown)] w-full min-w-[120px] overflow-hidden rounded-xl border p-1 shadow-2xl backdrop-blur-xl"
              style={{
                background: "rgba(10, 15, 25, 0.95)",
                borderColor: "var(--os-stroke)",
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

type StorageSummary = {
  graph_id?: string | null;
  total_files: number;
  total_bytes: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
};

type StorageBackends = {
  postgres: boolean;
  redis: boolean;
  qdrant: boolean;
  raw_store: boolean;
};

type UploadResult = {
  filename: string;
  status: string;
  raw_id?: string | null;
  packet_hash?: string | null;
  node_count: number;
  vector_count: number;
  error?: string | null;
  requested_profile?: string | null;
  requested_persist_mode?: string | null;
  requested_extractor_mode?: string | null;
  effective_profile?: string | null;
  effective_persist_mode?: string | null;
  effective_extractor_mode?: string | null;
  durability_path?: string | null;
};

type UploadBatchResponse = {
  job_id: string;
  graph_id: string;
  status: string;
  requested_files: number;
  processed_files: number;
  success_files: number;
  failed_files: number;
  dedup_hits: number;
  cancelled_files: number;
  files: UploadResult[];
  requested_profile?: string | null;
  requested_persist_mode?: string | null;
  requested_extractor_mode?: string | null;
  effective_profile?: string | null;
  effective_persist_mode?: string | null;
  effective_extractor_mode?: string | null;
  durability_path?: string | null;
};

type UploadStatusResponse = {
  job_id: string;
  graph_id: string;
  status: string;
  requested_files: number;
  processed_files: number;
  success_files: number;
  failed_files: number;
  dedup_hits: number;
  cancelled_files: number;
  cancel_requested: boolean;
  cancel_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  completed_at?: string | null;
  files: StorageFileItem[];
  requested_profile?: string | null;
  requested_persist_mode?: string | null;
  requested_extractor_mode?: string | null;
  effective_profile?: string | null;
  effective_persist_mode?: string | null;
  effective_extractor_mode?: string | null;
  durability_path?: string | null;
};

type StorageJobEvent = {
  seq: number;
  kind: string;
  ts?: string | null;
  payload: Record<string, unknown>;
};

type StorageJobEventsResponse = {
  job_id: string;
  events: StorageJobEvent[];
};

type StorageUploadCancelResponse = {
  job_id: string;
  status: string;
  cancel_requested: boolean;
  cancel_reason?: string | null;
};

type StorageIngestActionResponse = {
  status: string;
  file: StorageFileItem;
  ingest: {
    status: string;
    packet_hash?: string | null;
    nodes_written?: number;
    vector_count?: number;
    error?: string | null;
    requested_profile?: string | null;
    requested_persist_mode?: string | null;
    requested_extractor_mode?: string | null;
    effective_profile?: string | null;
    effective_persist_mode?: string | null;
    effective_extractor_mode?: string | null;
    durability_path?: string | null;
  };
};

type StorageSupportedTypesResponse = {
  max_batch_total_bytes: number;
  max_batch_total_mb: number;
  total_extensions: number;
  total_content_types: number;
  extensions: string[];
  content_types: string[];
  categories: Record<string, string[]>;
  extractor_doc_types: Record<string, number>;
  ocr_enabled: boolean;
  ocr_engine: string;
  ocr_fail_closed: boolean;
  ocr_capable_extensions: string[];
};

type StorageDomainMemoryTerm = {
  surface_form: string;
  canonical_form: string;
  kind: string;
  domain_pack?: string | null;
  support_count: number;
  score: number;
  node_id?: string | null;
  has_node: boolean;
  meta: Record<string, unknown>;
};

type StorageDomainMemorySource = {
  source_kind: string;
  count: number;
};

type StorageDomainMemoryResponse = {
  graph_id: string;
  graph_version: number;
  jobs_enabled: boolean;
  domain_autonomy_enabled: boolean;
  lexicon_total: number;
  source_total: number;
  detected_packs: string[];
  source_kinds: Record<string, number>;
  top_terms: StorageDomainMemoryTerm[];
  top_sources: StorageDomainMemorySource[];
  last_updated_at?: string | null;
};

type StorageProvenanceRawRef = {
  raw_id: string;
  sha256: string;
  uri: string;
  mime_type: string;
  size_bytes: number;
  created_at?: string | null;
};

type StorageProvenanceDedup = {
  packet_hash?: string | null;
  dedup_record_found: boolean;
  dedup_raw_id?: string | null;
  dedup_node_count: number;
  dedup_created_at?: string | null;
};

type StorageProvenanceNode = {
  node_id: string;
  kind: string;
  vector_hash: string;
  block_id?: string | null;
  created_at?: string | null;
};

type StorageProvenanceEvent = {
  seq: number;
  kind: string;
  ts?: string | null;
  payload_keys: string[];
  payload: Record<string, unknown>;
};

type StorageProvenanceResponse = {
  file: StorageFileItem;
  raw_ref?: StorageProvenanceRawRef | null;
  dedup: StorageProvenanceDedup;
  node_count: number;
  event_count: number;
  nodes: StorageProvenanceNode[];
  events: StorageProvenanceEvent[];
};

type FileListResponse = {
  items: StorageFileItem[];
  total: number;
  limit: number;
  offset: number;
};

type QueueStatus =
  | "queued"
  | "uploading"
  | "ingesting"
  | "ingested"
  | "dedup_hit"
  | "failed"
  | "cancelled";

type ExtractorMode = "faim_native";

type QueueItem = {
  id: string;
  file: File;
  filename: string;
  sizeBytes: number;
  mimeType: string;
  graphId: string;
  status: QueueStatus;
  progress: number;
  jobId?: string;
  rawId?: string;
  packetHash?: string | null;
  nodeCount: number;
  vectorCount: number;
  error?: string;
  cancelRequested: boolean;
  events: StorageJobEvent[];
  lastEventSeq: number;
  createdAt: number;
  updatedAt: number;
  busyAction?: "cancel" | "retry";
  requestedProfile?: string | null;
  requestedPersistMode?: string | null;
  requestedExtractorMode?: ExtractorMode;
  effectiveProfile?: string | null;
  effectivePersistMode?: string | null;
  effectiveExtractorMode?: ExtractorMode;
  durabilityPath?: string | null;
};

const PAGE_SIZE = 20;
const MAX_UPLOAD_CONCURRENCY = 3;
const MAX_QUEUE_ITEMS = 120;
const MAX_QUEUE_EVENTS = 60;
const JOB_POLL_INTERVAL_MS = 5000;
const TERMINAL_QUEUE_STATUS = new Set<QueueStatus>([
  "ingested",
  "dedup_hit",
  "failed",
  "cancelled",
]);

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const exp = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / Math.pow(1024, exp);
  return `${value.toFixed(value >= 100 || exp === 0 ? 0 : 1)} ${units[exp]}`;
}

function statusVariant(
  status: string,
): "default" | "success" | "warning" | "error" | "info" {
  if (status === "ingested" || status === "dedup_hit") return "success";
  if (status === "failed" || status === "cancelled") return "error";
  if (status === "ingesting" || status === "uploading") return "info";
  if (status === "delete_requested") return "warning";
  return "default";
}

function shortId(value?: string | null): string {
  if (!value) return "-";
  if (value.length <= 14) return value;
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function redactUri(uri?: string | null): string {
  if (!uri) return "-";
  if (uri.length <= 28) return uri;
  return `${uri.slice(0, 16)}...${uri.slice(-12)}`;
}

function mapStorageStatus(status?: string | null): QueueStatus {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "ingested" || normalized === "completed")
    return "ingested";
  if (normalized === "dedup_hit") return "dedup_hit";
  if (normalized === "failed" || normalized === "error") return "failed";
  if (normalized === "cancelled") return "cancelled";
  if (normalized === "ingesting" || normalized === "running")
    return "ingesting";
  if (
    normalized === "uploading" ||
    normalized === "uploaded" ||
    normalized === "pending" ||
    normalized === "queued"
  )
    return "queued";
  return "queued";
}

function queueProgress(status: QueueStatus): number {
  if (status === "queued") return 0;
  if (status === "uploading") return 30;
  if (status === "ingesting") return 75;
  return 100;
}

function safeNow(): number {
  return Date.now();
}

function latestMessage(item: QueueItem): string {
  const last = item.events[item.events.length - 1];
  if (!last) {
    if (item.error) return item.error;
    if (item.cancelRequested) return "Cancel requested";
    return "Waiting";
  }

  const message =
    typeof last.payload?.message === "string"
      ? String(last.payload.message)
      : "";
  const status =
    typeof last.payload?.status === "string" ? String(last.payload.status) : "";

  if (message) return message;
  if (status) return status;
  return last.kind;
}

function modeSummary(item: QueueItem): string | null {
  const hasMode =
    item.requestedProfile ||
    item.requestedPersistMode ||
    item.effectiveProfile ||
    item.effectivePersistMode ||
    item.durabilityPath;
  if (!hasMode) return null;
  return buildEffectiveModeText(
    item.requestedProfile,
    item.requestedPersistMode,
    item.effectiveProfile,
    item.effectivePersistMode,
    item.durabilityPath,
  );
}

function extractorModeLabel(_mode?: string | null): string {
  return "FAIM Native";
}

async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const base: Record<string, string> = {};
  if (token) base.Authorization = `Bearer ${token}`;

  if (!extra) return base;

  if (extra instanceof Headers) {
    extra.forEach((value, key) => {
      base[key] = value;
    });
    return base;
  }

  if (Array.isArray(extra)) {
    for (const [key, value] of extra) base[key] = value;
    return base;
  }

  return { ...base, ...(extra as Record<string, string>) };
}

function normalizeApiError(payload: unknown, fallback: string): string {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (typeof payload === "object") {
    const data = payload as {
      detail?: unknown;
      error?: unknown;
      message?: unknown;
    };
    const detail = data.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    const error = data.error;
    if (typeof error === "string" && error.trim()) return error;
    const message = data.message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}

function trimQueue(items: QueueItem[]): QueueItem[] {
  if (items.length <= MAX_QUEUE_ITEMS) return items;
  const terminal = items.filter((i) => TERMINAL_QUEUE_STATUS.has(i.status));
  const active = items.filter((i) => !TERMINAL_QUEUE_STATUS.has(i.status));
  const removable = [...terminal].sort((a, b) => a.updatedAt - b.updatedAt);
  while (active.length + removable.length > MAX_QUEUE_ITEMS) {
    removable.shift();
  }
  return [...active, ...removable].sort((a, b) => a.createdAt - b.createdAt);
}

export default function StoragePage() {
  const { data: session, status: sessionStatus } = useSession();
  const { toast } = useToast();
  const accessToken = (session as { accessToken?: string } | null)?.accessToken;
  const isAuthenticated =
    sessionStatus === "authenticated" && Boolean(accessToken);

  const sessionGraphId =
    (session as { graphId?: string } | null)?.graphId || "default";
  const [graphScopeInput, setGraphScopeInput] = useState(sessionGraphId);
  const [graphScope, setGraphScope] = useState(sessionGraphId);

  const [files, setFiles] = useState<StorageFileItem[]>([]);
  const [summary, setSummary] = useState<StorageSummary | null>(null);
  const [backends, setBackends] = useState<StorageBackends | null>(null);
  const [supportedTypes, setSupportedTypes] =
    useState<StorageSupportedTypesResponse | null>(null);
  const [domainMemory, setDomainMemory] =
    useState<StorageDomainMemoryResponse | null>(null);
  const [total, setTotal] = useState(0);

  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const [loadingFiles, setLoadingFiles] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingDomainMemory, setLoadingDomainMemory] = useState(false);
  const [actionRawId, setActionRawId] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [profile, setProfile] = useState("strict");
  const [persistMode, setPersistMode] = useState("relaxed");
  const [extractorMode, setExtractorMode] =
    useState<ExtractorMode>("faim_native");

  const ingestModePolicy = useMemo(
    () => resolveUiModePolicy("ingest", profile, persistMode),
    [persistMode, profile],
  );
  const activeGraphId = useMemo(
    () => graphScope.trim() || sessionGraphId,
    [graphScope, sessionGraphId],
  );
  const selectedModeLabel = useMemo(
    () => formatModePair(profile, persistMode),
    [persistMode, profile],
  );
  const selectedExtractorLabel = useMemo(
    () => extractorModeLabel(extractorMode),
    [extractorMode],
  );

  const [provenanceOpen, setProvenanceOpen] = useState(false);
  const [provenanceLoading, setProvenanceLoading] = useState(false);
  const [provenanceView, setProvenanceView] = useState<"faim" | "technical">(
    "faim",
  );
  const [provenanceRawId, setProvenanceRawId] = useState<string | null>(null);
  const [provenanceData, setProvenanceData] =
    useState<StorageProvenanceResponse | null>(null);
  const [supportedTypesOpen, setSupportedTypesOpen] = useState(false);
  const [supportedTypesLoading, setSupportedTypesLoading] = useState(false);

  const queueRef = useRef<QueueItem[]>([]);
  const uploadControllersRef = useRef<Map<string, AbortController>>(new Map());
  const refreshLockRef = useRef(false);
  const toastRef = useRef(toast);
  const toastDedupRef = useRef<Record<string, number>>({});

  useEffect(() => {
    queueRef.current = queueItems;
  }, [queueItems]);

  useEffect(() => {
    toastRef.current = toast;
  }, [toast]);

  const throttledToast = useCallback(
    (
      kind: "error" | "warning" | "info" | "success",
      title: string,
      description: string,
      dedupKey: string,
      windowMs = 30000,
    ) => {
      const now = safeNow();
      const last = toastDedupRef.current[dedupKey] || 0;
      if (now - last < windowMs) return;
      toastDedupRef.current[dedupKey] = now;
      toastRef.current[kind](title, description);
    },
    [],
  );

  const totalPages = useMemo(() => {
    if (!total) return 1;
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }, [total]);

  const queueCounts = useMemo(() => {
    const counts: Record<QueueStatus, number> = {
      queued: 0,
      uploading: 0,
      ingesting: 0,
      ingested: 0,
      dedup_hit: 0,
      failed: 0,
      cancelled: 0,
    };
    for (const item of queueItems) {
      counts[item.status] += 1;
    }
    return counts;
  }, [queueItems]);

  const fetchJson = useCallback(
    async <T,>(url: string, init?: RequestInit): Promise<T> => {
      const headers = await authHeaders(init?.headers);
      const response = await fetch(url, {
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

      return (payload as T) || ({} as T);
    },
    [],
  );

  const fetchFilesInternal = useCallback(async () => {
    setLoadingFiles(true);
    try {
      const params = new URLSearchParams({
        graph_id: activeGraphId,
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
        include_delete_requested: "true",
      });
      if (statusFilter && statusFilter !== "all")
        params.set("status", statusFilter);
      if (query.trim()) params.set("q", query.trim());

      const data = await fetchJson<FileListResponse>(
        `/api/v1/storage/files?${params.toString()}`,
      );
      setFiles(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      if (error instanceof ApiError && error.status === 429) {
        throttledToast(
          "warning",
          "Storage list rate-limited",
          message,
          "storage-files-429",
        );
      } else {
        throttledToast(
          "error",
          "Failed to load storage files",
          message,
          "storage-files-error",
          15000,
        );
      }
    } finally {
      setLoadingFiles(false);
    }
  }, [activeGraphId, fetchJson, page, query, statusFilter, throttledToast]);

  const fetchSummaryInternal = useCallback(async () => {
    setLoadingSummary(true);
    try {
      const [summaryData, backendData] = await Promise.all([
        fetchJson<StorageSummary>(
          `/api/v1/storage/summary?graph_id=${encodeURIComponent(activeGraphId)}`,
        ),
        fetchJson<StorageBackends>(`/api/v1/storage/backends/health`),
      ]);
      setSummary(summaryData);
      setBackends(backendData);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      if (error instanceof ApiError && error.status === 429) {
        throttledToast(
          "warning",
          "Storage summary rate-limited",
          message,
          "storage-summary-429",
        );
      } else {
        throttledToast(
          "warning",
          "Storage summary unavailable",
          message,
          "storage-summary-error",
          20000,
        );
      }
    } finally {
      setLoadingSummary(false);
    }
  }, [activeGraphId, fetchJson, throttledToast]);

  const fetchDomainMemoryInternal = useCallback(async () => {
    setLoadingDomainMemory(true);
    try {
      const data = await fetchJson<StorageDomainMemoryResponse>(
        `/api/v1/storage/domain-memory?graph_id=${encodeURIComponent(activeGraphId)}&limit=8`,
      );
      setDomainMemory(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      if (error instanceof ApiError && error.status === 429) {
        throttledToast(
          "warning",
          "Domain memory rate-limited",
          message,
          "storage-domain-memory-429",
        );
      } else {
        throttledToast(
          "warning",
          "Domain memory unavailable",
          message,
          "storage-domain-memory-error",
          20000,
        );
      }
    } finally {
      setLoadingDomainMemory(false);
    }
  }, [activeGraphId, fetchJson, throttledToast]);

  const fetchSupportedTypesInternal = useCallback(async () => {
    setSupportedTypesLoading(true);
    try {
      const data = await fetchJson<StorageSupportedTypesResponse>(
        `/api/v1/storage/supported-types`,
      );
      setSupportedTypes(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      if (error instanceof ApiError && error.status === 429) {
        throttledToast(
          "warning",
          "Supported files rate-limited",
          message,
          "storage-supported-429",
        );
      } else {
        throttledToast(
          "warning",
          "Supported file coverage unavailable",
          message,
          "storage-supported-error",
          20000,
        );
      }
    } finally {
      setSupportedTypesLoading(false);
    }
  }, [fetchJson, throttledToast]);

  const openSupportedTypes = useCallback(() => {
    setSupportedTypesOpen(true);
    if (!supportedTypes && !supportedTypesLoading) {
      void fetchSupportedTypesInternal();
    }
  }, [fetchSupportedTypesInternal, supportedTypes, supportedTypesLoading]);

  const refreshViews = useCallback(async () => {
    if (refreshLockRef.current) return;
    refreshLockRef.current = true;
    try {
      await Promise.all([
        fetchFilesInternal(),
        fetchSummaryInternal(),
        fetchDomainMemoryInternal(),
      ]);
    } finally {
      refreshLockRef.current = false;
    }
  }, [fetchDomainMemoryInternal, fetchFilesInternal, fetchSummaryInternal]);

  const applyGraphScope = useCallback(() => {
    const next = graphScopeInput.trim() || sessionGraphId;
    if (next === graphScope) return;
    setGraphScope(next);
    setPage(0);
    setQueueItems([]);
    toast.info("Graph scope updated", `Storage now targets ${next}`);
  }, [graphScope, graphScopeInput, sessionGraphId, toast]);

  const patchQueueItem = useCallback(
    (itemId: string, updater: (item: QueueItem) => QueueItem) => {
      setQueueItems((prev) =>
        prev.map((item) => (item.id === itemId ? updater(item) : item)),
      );
    },
    [],
  );

  const appendQueueEvents = useCallback(
    (itemId: string, incoming: StorageJobEvent[]) => {
      if (!incoming.length) return;
      patchQueueItem(itemId, (current) => {
        const seen = new Set<number>(current.events.map((event) => event.seq));
        const merged = [...current.events];
        for (const event of incoming) {
          if (!seen.has(event.seq)) merged.push(event);
        }
        merged.sort((a, b) => a.seq - b.seq);
        const trimmed = merged.slice(-MAX_QUEUE_EVENTS);
        const latestSeq = trimmed.length
          ? trimmed[trimmed.length - 1].seq
          : current.lastEventSeq;
        return {
          ...current,
          events: trimmed,
          lastEventSeq: Math.max(current.lastEventSeq, latestSeq),
          updatedAt: safeNow(),
        };
      });
    },
    [patchQueueItem],
  );

  const refreshQueueJob = useCallback(
    async (itemId: string, jobId: string) => {
      const current = queueRef.current.find((item) => item.id === itemId);
      if (!current || TERMINAL_QUEUE_STATUS.has(current.status)) return;

      try {
        const [statusData, eventsData] = await Promise.all([
          fetchJson<UploadStatusResponse>(
            `/api/v1/storage/uploads/${encodeURIComponent(jobId)}`,
          ),
          fetchJson<StorageJobEventsResponse>(
            `/api/v1/storage/uploads/${encodeURIComponent(jobId)}/events`,
          ),
        ]);

        const fileMatch =
          statusData.files.find((row) =>
            current.rawId
              ? row.raw_id === current.rawId
              : row.filename === current.filename,
          ) || statusData.files[0];

        const nextEvents = (eventsData.events || []).filter(
          (event) => event.seq > current.lastEventSeq,
        );
        appendQueueEvents(itemId, nextEvents);

        const storageStatus = fileMatch?.ingest_status || statusData.status;
        let nextStatus = mapStorageStatus(storageStatus);
        if (statusData.status === "cancelled") nextStatus = "cancelled";

        const nextProgress = TERMINAL_QUEUE_STATUS.has(nextStatus)
          ? 100
          : nextStatus === "ingesting"
            ? 78
            : nextStatus === "uploading"
              ? 35
              : queueProgress(nextStatus);

        const wasTerminal = TERMINAL_QUEUE_STATUS.has(current.status);
        const nowTerminal = TERMINAL_QUEUE_STATUS.has(nextStatus);

        patchQueueItem(itemId, (item) => ({
          ...item,
          status: nextStatus,
          progress: nextProgress,
          jobId,
          rawId: fileMatch?.raw_id || item.rawId,
          packetHash: fileMatch?.packet_hash ?? item.packetHash,
          nodeCount: fileMatch?.node_count ?? item.nodeCount,
          vectorCount: fileMatch?.vector_count ?? item.vectorCount,
          requestedProfile:
            statusData.requested_profile ?? item.requestedProfile,
          requestedPersistMode:
            statusData.requested_persist_mode ?? item.requestedPersistMode,
          requestedExtractorMode:
            (statusData.requested_extractor_mode as
              | ExtractorMode
              | null
              | undefined) ?? item.requestedExtractorMode,
          effectiveProfile:
            statusData.effective_profile ?? item.effectiveProfile,
          effectivePersistMode:
            statusData.effective_persist_mode ?? item.effectivePersistMode,
          effectiveExtractorMode:
            (statusData.effective_extractor_mode as
              | ExtractorMode
              | null
              | undefined) ?? item.effectiveExtractorMode,
          durabilityPath: statusData.durability_path ?? item.durabilityPath,
          error: fileMatch?.error || item.error,
          cancelRequested: statusData.cancel_requested || item.cancelRequested,
          updatedAt: safeNow(),
        }));

        if (!wasTerminal && nowTerminal) {
          await refreshViews();
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          patchQueueItem(itemId, (item) => ({
            ...item,
            status: "failed",
            progress: 100,
            error: "Upload job no longer available",
            updatedAt: safeNow(),
          }));
          return;
        }

        const message =
          error instanceof Error ? error.message : "Unknown error";
        patchQueueItem(itemId, (item) => ({
          ...item,
          error: message,
          updatedAt: safeNow(),
        }));
      }
    },
    [appendQueueEvents, fetchJson, patchQueueItem, refreshViews],
  );

  const enqueueFiles = useCallback(
    (incomingFiles: File[]) => {
      const modePolicy = resolveUiModePolicy("ingest", profile, persistMode);
      if (!modePolicy.supported) {
        toast.warning(
          "Unsupported mode combination",
          modePolicy.reason || "Choose a supported profile/persist mode.",
        );
        return;
      }
      const accepted: QueueItem[] = [];
      const rejected: string[] = [];

      for (const file of incomingFiles) {
        const name = (file.name || "").trim();
        if (!name) {
          rejected.push("unnamed file");
          continue;
        }
        if (!Number.isFinite(file.size) || file.size < 0) {
          rejected.push(name);
          continue;
        }
        if (!(file.type || "").trim()) {
          rejected.push(name);
          continue;
        }

        const now = safeNow();
        accepted.push({
          id: `${now}-${Math.random().toString(36).slice(2, 8)}`,
          file,
          filename: name,
          sizeBytes: file.size,
          mimeType: file.type,
          status: "queued",
          progress: 0,
          nodeCount: 0,
          vectorCount: 0,
          cancelRequested: false,
          events: [],
          lastEventSeq: 0,
          createdAt: now,
          updatedAt: now,
          graphId: activeGraphId,
          requestedExtractorMode: extractorMode,
          effectiveExtractorMode: extractorMode,
        });
      }

      if (rejected.length) {
        toast.warning(
          "Some files were rejected",
          `${rejected.length} file(s) missing required client metadata (name/type/size)`,
        );
      }

      if (!accepted.length) return;

      setQueueItems((prev) => trimQueue([...prev, ...accepted]));
    },
    [activeGraphId, extractorMode, persistMode, profile, toast],
  );

  const startQueueUpload = useCallback(
    async (itemId: string) => {
      const current = queueRef.current.find((item) => item.id === itemId);
      if (!current || current.status !== "queued") return;
      const modePolicy = resolveUiModePolicy("ingest", profile, persistMode);
      if (!modePolicy.supported) {
        patchQueueItem(itemId, (item) => ({
          ...item,
          status: "failed",
          progress: 100,
          error:
            modePolicy.reason ||
            "Selected profile/persist mode is not allowed.",
          updatedAt: safeNow(),
        }));
        return;
      }

      const controller = new AbortController();
      uploadControllersRef.current.set(itemId, controller);

      patchQueueItem(itemId, (item) => ({
        ...item,
        status: "uploading",
        progress: 20,
        error: undefined,
        cancelRequested: false,
        updatedAt: safeNow(),
      }));

      try {
        const formData = new FormData();
        formData.set("graph_id", current.graphId || activeGraphId);
        formData.set("profile", profile);
        formData.set("persist_mode", persistMode);
        formData.set(
          "extractor_mode",
          current.requestedExtractorMode || extractorMode,
        );
        formData.append("files", current.file);

        const headers = await authHeaders();
        const response = await fetch(`/api/v1/storage/uploads`, {
          method: "POST",
          headers,
          body: formData,
          signal: controller.signal,
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
            normalizeApiError(payload, "Upload failed"),
          );
        }

        const batch = payload as UploadBatchResponse;
        const result = batch.files?.[0];
        const status = mapStorageStatus(result?.status || batch.status);

        patchQueueItem(itemId, (item) => ({
          ...item,
          status,
          progress: queueProgress(status),
          jobId: batch.job_id,
          rawId: result?.raw_id || item.rawId,
          packetHash: result?.packet_hash ?? item.packetHash,
          nodeCount: result?.node_count ?? item.nodeCount,
          vectorCount: result?.vector_count ?? item.vectorCount,
          requestedProfile:
            result?.requested_profile ??
            batch.requested_profile ??
            item.requestedProfile,
          requestedPersistMode:
            result?.requested_persist_mode ??
            batch.requested_persist_mode ??
            item.requestedPersistMode,
          requestedExtractorMode:
            (result?.requested_extractor_mode as
              | ExtractorMode
              | null
              | undefined) ??
            (batch.requested_extractor_mode as
              | ExtractorMode
              | null
              | undefined) ??
            item.requestedExtractorMode,
          effectiveProfile:
            result?.effective_profile ??
            batch.effective_profile ??
            item.effectiveProfile,
          effectivePersistMode:
            result?.effective_persist_mode ??
            batch.effective_persist_mode ??
            item.effectivePersistMode,
          effectiveExtractorMode:
            (result?.effective_extractor_mode as
              | ExtractorMode
              | null
              | undefined) ??
            (batch.effective_extractor_mode as
              | ExtractorMode
              | null
              | undefined) ??
            item.effectiveExtractorMode,
          durabilityPath:
            result?.durability_path ??
            batch.durability_path ??
            item.durabilityPath,
          error: result?.error || item.error,
          updatedAt: safeNow(),
        }));

        if (batch.job_id) {
          await refreshQueueJob(itemId, batch.job_id);
        }

        if (TERMINAL_QUEUE_STATUS.has(status)) {
          await refreshViews();
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          patchQueueItem(itemId, (item) => ({
            ...item,
            status: "cancelled",
            progress: 100,
            error: "Upload cancelled before completion",
            cancelRequested: true,
            updatedAt: safeNow(),
          }));
          return;
        }

        const message =
          error instanceof Error ? error.message : "Unknown error";
        patchQueueItem(itemId, (item) => ({
          ...item,
          status: "failed",
          progress: 100,
          error: message,
          updatedAt: safeNow(),
        }));
      } finally {
        uploadControllersRef.current.delete(itemId);
      }
    },
    [
      activeGraphId,
      extractorMode,
      patchQueueItem,
      persistMode,
      profile,
      refreshQueueJob,
      refreshViews,
    ],
  );

  const requestQueueCancel = useCallback(
    async (itemId: string) => {
      const current = queueRef.current.find((item) => item.id === itemId);
      if (
        !current ||
        TERMINAL_QUEUE_STATUS.has(current.status) ||
        current.busyAction
      )
        return;

      patchQueueItem(itemId, (item) => ({
        ...item,
        busyAction: "cancel",
        updatedAt: safeNow(),
      }));

      try {
        if (current.status === "queued") {
          patchQueueItem(itemId, (item) => ({
            ...item,
            status: "cancelled",
            progress: 100,
            cancelRequested: true,
            busyAction: undefined,
            error: "Cancelled before upload started",
            updatedAt: safeNow(),
          }));
          return;
        }

        if (current.jobId) {
          const data = await fetchJson<StorageUploadCancelResponse>(
            `/api/v1/storage/uploads/${encodeURIComponent(current.jobId)}/cancel?reason=${encodeURIComponent("Requested from storage UI")}`,
            { method: "POST" },
          );

          const status = mapStorageStatus(data.status);
          patchQueueItem(itemId, (item) => ({
            ...item,
            status,
            cancelRequested: data.cancel_requested || true,
            busyAction: undefined,
            updatedAt: safeNow(),
          }));
          if (status === "cancelled") {
            await refreshViews();
          }
          return;
        }

        const controller = uploadControllersRef.current.get(itemId);
        if (controller) controller.abort();

        patchQueueItem(itemId, (item) => ({
          ...item,
          status: "cancelled",
          progress: 100,
          cancelRequested: true,
          busyAction: undefined,
          updatedAt: safeNow(),
        }));
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Unknown error";
        patchQueueItem(itemId, (item) => ({
          ...item,
          busyAction: undefined,
          error: message,
          updatedAt: safeNow(),
        }));
      }
    },
    [fetchJson, patchQueueItem, refreshViews],
  );

  const retryQueueItem = useCallback(
    async (itemId: string) => {
      const current = queueRef.current.find((item) => item.id === itemId);
      if (!current || current.busyAction) return;
      if (!(current.status === "failed" || current.status === "cancelled"))
        return;
      const modePolicy = resolveUiModePolicy("ingest", profile, persistMode);
      if (!modePolicy.supported) {
        toast.warning(
          "Unsupported mode combination",
          modePolicy.reason || "Choose a supported profile/persist mode.",
        );
        return;
      }

      patchQueueItem(itemId, (item) => ({
        ...item,
        busyAction: "retry",
        updatedAt: safeNow(),
      }));

      try {
        if (!current.rawId) {
          patchQueueItem(itemId, (item) => ({
            ...item,
            status: "queued",
            progress: 0,
            jobId: undefined,
            packetHash: undefined,
            nodeCount: 0,
            vectorCount: 0,
            requestedProfile: undefined,
            requestedPersistMode: undefined,
            requestedExtractorMode: undefined,
            effectiveProfile: undefined,
            effectivePersistMode: undefined,
            effectiveExtractorMode: undefined,
            durabilityPath: undefined,
            error: undefined,
            cancelRequested: false,
            busyAction: undefined,
            events: [],
            lastEventSeq: 0,
            updatedAt: safeNow(),
          }));
          return;
        }

        patchQueueItem(itemId, (item) => ({
          ...item,
          status: "ingesting",
          progress: 78,
          jobId: undefined,
          error: undefined,
          cancelRequested: false,
          busyAction: "retry",
          updatedAt: safeNow(),
        }));

        const data = await fetchJson<StorageIngestActionResponse>(
          `/api/v1/storage/files/${encodeURIComponent(current.rawId)}/retry?graph_id=${encodeURIComponent(current.graphId || activeGraphId)}&profile=${encodeURIComponent(profile)}&persist_mode=${encodeURIComponent(persistMode)}&extractor_mode=${encodeURIComponent(extractorMode)}`,
          { method: "POST" },
        );

        const status = mapStorageStatus(
          data.ingest?.status || data.file?.ingest_status || data.status,
        );

        patchQueueItem(itemId, (item) => ({
          ...item,
          status,
          progress: queueProgress(status),
          jobId: undefined,
          rawId: data.file?.raw_id || item.rawId,
          packetHash: data.ingest?.packet_hash ?? item.packetHash,
          nodeCount: data.file?.node_count ?? item.nodeCount,
          vectorCount: data.file?.vector_count ?? item.vectorCount,
          requestedProfile:
            data.ingest?.requested_profile ?? item.requestedProfile,
          requestedPersistMode:
            data.ingest?.requested_persist_mode ?? item.requestedPersistMode,
          requestedExtractorMode:
            (data.ingest?.requested_extractor_mode as
              | ExtractorMode
              | null
              | undefined) ?? item.requestedExtractorMode,
          effectiveProfile:
            data.ingest?.effective_profile ?? item.effectiveProfile,
          effectivePersistMode:
            data.ingest?.effective_persist_mode ?? item.effectivePersistMode,
          effectiveExtractorMode:
            (data.ingest?.effective_extractor_mode as
              | ExtractorMode
              | null
              | undefined) ?? item.effectiveExtractorMode,
          durabilityPath: data.ingest?.durability_path ?? item.durabilityPath,
          error: data.ingest?.error || data.file?.error || undefined,
          busyAction: undefined,
          updatedAt: safeNow(),
        }));

        await refreshViews();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Unknown error";
        patchQueueItem(itemId, (item) => ({
          ...item,
          status: "failed",
          progress: 100,
          error: message,
          busyAction: undefined,
          updatedAt: safeNow(),
        }));
      }
    },
    [
      activeGraphId,
      extractorMode,
      fetchJson,
      patchQueueItem,
      persistMode,
      profile,
      refreshViews,
      toast,
    ],
  );

  const clearTerminalQueueItems = useCallback(() => {
    setQueueItems((prev) =>
      prev.filter((item) => !TERMINAL_QUEUE_STATUS.has(item.status)),
    );
  }, []);

  const removeQueueItem = useCallback((itemId: string) => {
    setQueueItems((prev) => prev.filter((item) => item.id !== itemId));
  }, []);

  const runFileAction = useCallback(
    async (rawId: string, action: "ingest" | "retry" | "delete") => {
      if (action !== "delete") {
        const modePolicy = resolveUiModePolicy("ingest", profile, persistMode);
        if (!modePolicy.supported) {
          toast.warning(
            "Unsupported mode combination",
            modePolicy.reason || "Choose a supported profile/persist mode.",
          );
          return;
        }
      }
      setActionRawId(rawId);
      try {
        let url = `/api/v1/storage/files/${encodeURIComponent(rawId)}`;
        let method = "POST";

        if (action === "ingest") {
          url += `/ingest?graph_id=${encodeURIComponent(activeGraphId)}&profile=${encodeURIComponent(profile)}&persist_mode=${encodeURIComponent(persistMode)}&extractor_mode=${encodeURIComponent(extractorMode)}`;
        } else if (action === "retry") {
          url += `/retry?graph_id=${encodeURIComponent(activeGraphId)}&profile=${encodeURIComponent(profile)}&persist_mode=${encodeURIComponent(persistMode)}&extractor_mode=${encodeURIComponent(extractorMode)}`;
        } else {
          method = "DELETE";
          url += `?graph_id=${encodeURIComponent(activeGraphId)}&reason=${encodeURIComponent("Requested from storage UI")}`;
        }

        const data = await fetchJson<StorageIngestActionResponse | unknown>(
          url,
          { method },
        );
        const ingestData =
          action === "delete"
            ? null
            : (data as StorageIngestActionResponse | null)?.ingest || null;
        const modeText = ingestData
          ? buildEffectiveModeText(
              ingestData.requested_profile,
              ingestData.requested_persist_mode,
              ingestData.effective_profile,
              ingestData.effective_persist_mode,
              ingestData.durability_path,
            )
          : null;

        if (action === "delete") {
          toast.info(
            "Delete request submitted",
            "File marked as delete_requested",
          );
        } else if (action === "retry") {
          toast.success("Retry completed", modeText || "File reprocessed");
        } else {
          toast.success("Re-ingest completed", modeText || "File reprocessed");
        }

        await refreshViews();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Unknown error";
        toast.error(`Failed to ${action}`, message);
      } finally {
        setActionRawId(null);
      }
    },
    [
      activeGraphId,
      extractorMode,
      fetchJson,
      persistMode,
      profile,
      refreshViews,
      toast,
    ],
  );

  const downloadStorageFile = useCallback(
    async (rawId: string, filename: string) => {
      setActionRawId(rawId);
      try {
        const headers = await authHeaders();
        const response = await fetch(
          `/api/v1/storage/files/${encodeURIComponent(rawId)}/download?graph_id=${encodeURIComponent(activeGraphId)}`,
          {
            method: "GET",
            headers,
          },
        );
        if (!response.ok) {
          const text = await response.text();
          let payload: unknown = null;
          if (text) {
            try {
              payload = JSON.parse(text);
            } catch {
              payload = text;
            }
          }
          throw new ApiError(
            response.status,
            normalizeApiError(payload, "Download failed"),
          );
        }

        const blob = await response.blob();
        const objectUrl = window.URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = filename || rawId;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
        toast.success("Download started", filename);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Unknown error";
        toast.error("Failed to download", message);
      } finally {
        setActionRawId(null);
      }
    },
    [activeGraphId, toast],
  );

  const openProvenance = useCallback(
    async (rawId: string, view: "faim" | "technical" = "faim") => {
      setProvenanceOpen(true);
      setProvenanceView(view);
      setProvenanceRawId(rawId);
      setProvenanceLoading(true);
      setProvenanceData(null);

      try {
        const data = await fetchJson<StorageProvenanceResponse>(
          `/api/v1/storage/files/${encodeURIComponent(rawId)}/provenance?graph_id=${encodeURIComponent(activeGraphId)}`,
        );
        setProvenanceData(data);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Unknown error";
        toast.error("Failed to load provenance", message);
      } finally {
        setProvenanceLoading(false);
      }
    },
    [activeGraphId, fetchJson, toast],
  );

  useEffect(() => {
    if (!isAuthenticated) return;
    setGraphScopeInput(sessionGraphId);
    setGraphScope(sessionGraphId);
  }, [isAuthenticated, sessionGraphId]);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchFilesInternal();
  }, [fetchFilesInternal, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchSummaryInternal();
  }, [fetchSummaryInternal, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchDomainMemoryInternal();
  }, [fetchDomainMemoryInternal, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void fetchSupportedTypesInternal();
  }, [fetchSupportedTypesInternal, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const interval = window.setInterval(() => {
      fetchSummaryInternal();
    }, 15000);
    return () => window.clearInterval(interval);
  }, [fetchSummaryInternal, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const interval = window.setInterval(() => {
      fetchDomainMemoryInternal();
    }, 30000);
    return () => window.clearInterval(interval);
  }, [fetchDomainMemoryInternal, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const activeUploads = queueItems.filter(
      (item) => item.status === "uploading" || item.status === "ingesting",
    ).length;
    const capacity = MAX_UPLOAD_CONCURRENCY - activeUploads;
    if (capacity <= 0) return;

    const queued = queueItems
      .filter((item) => item.status === "queued")
      .slice(0, capacity);
    for (const item of queued) {
      void startQueueUpload(item.id);
    }
  }, [isAuthenticated, queueItems, startQueueUpload]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const pollTargets = queueItems.filter(
      (item) => item.jobId && !TERMINAL_QUEUE_STATUS.has(item.status),
    );
    if (!pollTargets.length) return;

    const poll = () => {
      for (const item of pollTargets) {
        if (!item.jobId) continue;
        void refreshQueueJob(item.id, item.jobId);
      }
    };

    poll();
    const timer = window.setInterval(poll, JOB_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [isAuthenticated, queueItems, refreshQueueJob]);

  useEffect(() => {
    if (!provenanceOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setProvenanceOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [provenanceOpen]);

  useEffect(() => {
    if (!supportedTypesOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSupportedTypesOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [supportedTypesOpen]);

  const onInputFiles = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const incoming = Array.from(event.target.files || []);
      enqueueFiles(incoming);
      event.currentTarget.value = "";
    },
    [enqueueFiles],
  );

  const onDropFiles = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragOver(false);
      const dropped = Array.from(event.dataTransfer.files || []);
      enqueueFiles(dropped);
    },
    [enqueueFiles],
  );

  const ingestedCount = summary?.by_status?.ingested || 0;
  const failedCount = summary?.by_status?.failed || 0;
  const dedupCount = summary?.by_status?.dedup_hit || 0;

  // ─── status helpers ───────────────────────────────────────
  function rowAccent(status: string, deleteReq: boolean) {
    if (deleteReq) return "border-l-[3px] border-l-[var(--faim-warning)]";
    if (status === "ingested" || status === "dedup_hit")
      return "border-l-[3px] border-l-[var(--faim-success)]";
    if (status === "failed")
      return "border-l-[3px] border-l-[var(--faim-error)]";
    if (["ingesting", "uploading", "queued"].includes(status))
      return "border-l-[3px] border-l-[var(--faim-info)]";
    return "border-l-[3px] border-l-transparent";
  }

  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader
        title="Storage Control"
        titleTestId="storage-page-title"
        subtitle={`Immutable Provenance & Ingest Lifecycle · Graph Scope: ${activeGraphId}`}
        icon={Database}
        actions={
          <div className="flex items-center gap-2">

            <label
              className="inline-flex cursor-pointer items-center gap-3 rounded-xl border border-white/5 bg-white/5 px-5 h-10 text-[11px] font-bold uppercase tracking-widest transition-all hover:bg-white/10 backdrop-blur-md shadow-sm"
              style={{ color: "var(--text-primary)" }}
            >
              <UploadCloud size={14} className="opacity-80" />
              Upload Matrix
              <input
                type="file"
                multiple
                className="hidden"
                onChange={onInputFiles}
                disabled={!ingestModePolicy.supported}
              />
            </label>
          </div>
        }
      />

      {!isAuthenticated && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Storage requires an active signed-in session. Sign out and sign back
          in if the page shows token errors or stale data.
        </div>
      )}

      {/* ── Graph Scope ─────────────────────────────────────── */}
      <div
        className="overflow-hidden rounded-xl border"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-1.5"
          style={{ borderColor: "var(--os-stroke)" }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-widest"
            style={{ color: "var(--text-tertiary)" }}
          >
            Graph Scope
          </p>

        </div>

        <div className="grid gap-3 px-5 py-4 md:grid-cols-3">
          <div>
            <p
              className="mb-1.5 text-[10px] font-medium uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Graph Scope
            </p>
            <Input
              value={graphScopeInput}
              onChange={(e) => setGraphScopeInput(e.target.value)}
              placeholder={sessionGraphId}
            />
          </div>
          <div className="flex items-end gap-2">
            <Button size="sm" variant="outline" onClick={applyGraphScope}>
              Apply Scope
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setGraphScopeInput(sessionGraphId);
                setGraphScope(sessionGraphId);
                setPage(0);
                setQueueItems([]);
              }}
            >
              Reset
            </Button>
          </div>
          <div
            className="rounded-lg border px-3 py-2 text-xs"
            style={{
              borderColor: "var(--os-stroke)",
              background: "var(--os-surface-2)",
              color: "var(--text-secondary)",
            }}
          >
            <p
              className="text-[10px] uppercase tracking-widest"
              style={{ color: "var(--text-tertiary)" }}
            >
              Scope summary
            </p>
            <p
              className="mt-1 font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              {activeGraphId}
            </p>
          </div>
        </div>
      </div>

      {/* ── Metric Strip ─────────────────────────────────────── */}
      <div
        className="grid grid-cols-2 overflow-hidden rounded-xl border xl:grid-cols-4"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        {[
          {
            label: "Total Files",
            value: summary?.total_files ?? 0,
            sub: "in graph",
            icon: <FileText size={18} />,
            accent: "var(--faim-info)",
            color: undefined,
          },
          {
            label: "Stored",
            value: formatBytes(summary?.total_bytes ?? 0),
            sub: "raw bytes",
            icon: <HardDrive size={18} />,
            accent: "var(--faim-secondary)",
            color: undefined,
          },
          {
            label: "Ingested",
            value: ingestedCount,
            sub: `Dedup hits: ${dedupCount}`,
            icon: <CheckCircle2 size={18} />,
            accent: "var(--faim-success)",
            color: "var(--faim-success-text)",
          },
          {
            label: "Failures",
            value: failedCount,
            sub: "needs retry",
            icon: <AlertCircle size={18} />,
            accent: failedCount > 0 ? "var(--faim-error)" : "var(--os-stroke)",
            color:
              failedCount > 0
                ? "var(--faim-error-text)"
                : "var(--text-tertiary)",
          },
        ].map((m, i) => (
          <div
            key={m.label}
            className="relative flex flex-col justify-center px-6 py-3"
            style={{
              borderLeft: i > 0 ? "1px solid var(--os-stroke)" : undefined,
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <p
                className="text-[10px] font-medium uppercase tracking-widest"
                style={{ color: "var(--text-tertiary)" }}
              >
                {m.label}
              </p>
              <div
                className="flex h-8 w-8 items-center justify-center rounded-lg border transition-all"
                style={{
                  background: `rgba(${m.accent === "var(--os-stroke)" ? "255,255,255" : "129,140,248"}, 0.03)`,
                  borderColor: m.accent,
                  color: m.accent,
                }}
              >
                {m.icon}
              </div>
            </div>
            <p
              className="font-semibold tabular-nums leading-none"
              style={{ fontSize: 26, color: m.color ?? "var(--text-primary)" }}
            >
              {m.value}
            </p>
            <p
              className="mt-2 text-[11px]"
              style={{ color: "var(--text-tertiary)" }}
            >
              {m.sub}
            </p>
          </div>
        ))}
      </div>

      {/* ── Domain Memory ───────────────────────────────────── */}
      <div
        className="overflow-hidden rounded-xl border"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-1.5"
          style={{ borderColor: "var(--os-stroke)" }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-widest"
            style={{ color: "var(--text-tertiary)" }}
          >
            Domain Memory
          </p>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<ServerCog size={12} />}
              onClick={() => {
                void fetchDomainMemoryInternal();
              }}
            >
              Refresh
            </Button>
            <Button
              size="sm"
              variant="ghost"
              leftIcon={
                domainMemory?.jobs_enabled ? (
                  <CheckCircle2 size={12} />
                ) : (
                  <AlertCircle size={12} />
                )
              }
            >
              Jobs {domainMemory?.jobs_enabled ? "enabled" : "disabled"}
            </Button>
          </div>
        </div>

        <div className="grid gap-4 px-5 py-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                {
                  label: "Domain autonomy",
                  value: domainMemory?.domain_autonomy_enabled
                    ? "enabled"
                    : "disabled",
                },
                {
                  label: "Lexicon rows",
                  value: domainMemory?.lexicon_total ?? 0,
                },
                {
                  label: "KB sources",
                  value: domainMemory?.source_total ?? 0,
                },
                {
                  label: "Graph version",
                  value: domainMemory?.graph_version ?? 0,
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-xl border px-3 py-2"
                  style={{
                    borderColor: "var(--os-stroke)",
                    background: "var(--os-surface-2)",
                  }}
                >
                  <p
                    className="text-[10px] uppercase tracking-wider"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    {item.label}
                  </p>
                  <p
                    className="mt-1 text-sm font-semibold"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {item.value}
                  </p>
                </div>
              ))}
            </div>

            <div
              className="rounded-xl border px-3 py-3"
              style={{
                borderColor: "var(--os-stroke)",
                background: "var(--os-surface-2)",
              }}
            >
              <p
                className="text-[10px] uppercase tracking-wider"
                style={{ color: "var(--text-tertiary)" }}
              >
                Detected packs
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(domainMemory?.detected_packs?.length
                  ? domainMemory.detected_packs
                  : ["general"]).map((pack) => (
                  <Badge key={pack} size="xs" variant="info">
                    {pack}
                  </Badge>
                ))}
              </div>
              <p
                className="mt-2 text-[11px]"
                style={{ color: "var(--text-tertiary)" }}
              >
                {domainMemory?.last_updated_at
                  ? `Last updated ${new Date(domainMemory.last_updated_at).toLocaleString()}`
                  : loadingDomainMemory
                    ? "Refreshing autonomous domain memory..."
                    : "Graph-local learning updates automatically after uploads and memory writes."}
              </p>
            </div>

            <div
              className="rounded-xl border px-3 py-3"
              style={{
                borderColor: "var(--os-stroke)",
                background: "var(--os-surface-2)",
              }}
            >
              <p
                className="text-[10px] uppercase tracking-wider"
                style={{ color: "var(--text-tertiary)" }}
              >
                Query-time effect
              </p>
              <p
                className="mt-1 text-xs leading-relaxed"
                style={{ color: "var(--text-secondary)" }}
              >
                Domain links are learned into the graph and then re-used by the
                query reranker. Open a query with `return_explain=true` to see
                linked terms and per-node domain score components.
              </p>
            </div>
          </div>

          <div
            className="rounded-2xl border p-4"
            style={{
              borderColor: "var(--os-stroke)",
              background: "linear-gradient(180deg, rgba(15,23,42,0.95), rgba(2,6,23,0.95))",
            }}
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <p
                  className="text-[10px] font-medium uppercase tracking-widest"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  Top learned terms
                </p>
                <p
                  className="mt-1 text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  What FAIM currently knows for this graph
                </p>
              </div>
              <Badge size="xs" variant="success">
                {domainMemory?.top_terms?.length ?? 0} shown
              </Badge>
            </div>

            <div className="mt-4 space-y-2 max-h-[280px] overflow-auto pr-1">
              {(domainMemory?.top_terms?.length
                ? domainMemory.top_terms
                : []).map((term) => (
                <div
                  key={`${term.surface_form}-${term.kind}-${term.canonical_form}`}
                  className="rounded-xl border px-3 py-2.5"
                  style={{
                    borderColor: "rgba(148,163,184,0.18)",
                    background: "rgba(15,23,42,0.65)",
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p
                        className="truncate text-sm font-medium"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {term.surface_form}
                      </p>
                      <p
                        className="mt-0.5 truncate text-[11px]"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        {term.kind} · {term.canonical_form}
                      </p>
                    </div>
                    <div className="text-right text-[11px] tabular-nums">
                      <p style={{ color: "var(--text-secondary)" }}>
                        support {term.support_count}
                      </p>
                      <p style={{ color: "var(--text-tertiary)" }}>
                        score {term.score.toFixed(2)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {term.domain_pack && (
                      <Badge size="xs" variant="info">
                        {term.domain_pack}
                      </Badge>
                    )}
                    <Badge
                      size="xs"
                      variant={term.has_node ? "success" : "warning"}
                    >
                      {term.has_node ? "graph-linked" : "learned"}
                    </Badge>
                  </div>
                </div>
              ))}
              {!domainMemory?.top_terms?.length && (
                <div
                  className="rounded-xl border border-dashed px-3 py-8 text-center text-xs"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {loadingDomainMemory
                    ? "Loading autonomous domain memory..."
                    : "No learned domain memory yet for this graph."}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Upload Panel ─────────────────────────────────────── */}
      <div
        className="overflow-hidden rounded-xl border"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        {/* Section header */}
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-1.5"
          style={{ borderColor: "var(--os-stroke)" }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-widest"
            style={{ color: "var(--text-tertiary)" }}
          >
            Upload Panel
          </p>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<FileText size={12} />}
              data-testid="storage-supported-types-open"
              onClick={openSupportedTypes}
            >
              Supported Files
              {supportedTypes ? ` (${supportedTypes.total_extensions})` : ""}
            </Button>
            <Button size="sm" variant="ghost" onClick={clearTerminalQueueItems}>
              Clear Completed
            </Button>
          </div>
        </div>

        {/* Hero Drop Zone */}
        <motion.div
          whileHover={{ backgroundColor: "rgba(99,102,241,0.04)" }}
          animate={
            isDragOver
              ? {
                  borderColor: "rgba(99,102,241,0.9)",
                  backgroundColor: "rgba(99,102,241,0.06)",
                }
              : { borderColor: "rgba(255,255,255,0.1)" }
          }
          transition={{ duration: 0.2 }}
          className="mx-5 mt-5 flex h-36 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed"
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={onDropFiles}
          onClick={() => document.getElementById("storage-file-input")?.click()}
        >
          <div
            className="flex h-9 w-9 items-center justify-center rounded-lg"
            style={{ background: "rgba(99,102,241,0.12)", color: "#818cf8" }}
          >
            <UploadCloud size={18} />
          </div>
          <p
            className="text-sm font-medium"
            style={{ color: "var(--text-primary)" }}
          >
            Drop files here or click to browse
          </p>
          <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
            Multi-file append-only · Queue keeps in-flight work
          </p>
          <input
            id="storage-file-input"
            type="file"
            multiple
            className="hidden"
            onChange={onInputFiles}
            disabled={!ingestModePolicy.supported}
          />
        </motion.div>

        {/* Controls row */}
        <div className="grid grid-cols-4 gap-3 px-5 pb-4 pt-4">
          {[
            {
              label: "Profile",
              node: (
                <ThemedSelect
                  value={profile}
                  onChange={setProfile}
                  options={[
                    { value: "strict", label: "strict" },
                    { value: "fast", label: "fast" },
                    { value: "relaxed", label: "relaxed" },
                  ]}
                />
              ),
            },
            {
              label: "Persist Mode",
              node: (
                <ThemedSelect
                  value={persistMode}
                  onChange={setPersistMode}
                  options={[
                    { value: "relaxed", label: "relaxed" },
                    { value: "strict", label: "strict" },
                  ]}
                />
              ),
            },
            {
              label: "Extractor",
              node: (
                <div
                  className="flex h-8 items-center rounded-lg border px-2.5 text-xs font-medium"
                  style={{
                    background: "var(--os-surface-2)",
                    borderColor: "var(--os-stroke)",
                    color: "var(--text-secondary)",
                  }}
                >
                  FAIM Native
                </div>
              ),
            },
            {
              label: "Queue Depth",
              node: (
                <div
                  className="flex h-8 items-center rounded-lg border px-2.5 text-xs tabular-nums"
                  style={{
                    background: "var(--os-surface-2)",
                    borderColor: "var(--os-stroke)",
                    color: "var(--text-secondary)",
                  }}
                >
                  {queueItems.length} item(s)
                </div>
              ),
            },
          ].map((c) => (
            <div key={c.label}>
              <p
                className="mb-1.5 text-[10px] font-medium uppercase tracking-wider"
                style={{ color: "var(--text-tertiary)" }}
              >
                {c.label}
              </p>
              {c.node}
            </div>
          ))}
        </div>

        {/* Mode info */}
        <div
          className={`mx-5 mb-4 rounded-lg border px-3.5 py-2.5 text-[11px] leading-relaxed ${
            ingestModePolicy.supported
              ? ""
              : "border-[var(--faim-error)]/30 bg-[var(--faim-error-muted)]"
          }`}
          style={
            ingestModePolicy.supported
              ? {
                  borderColor: "rgba(99,102,241,0.18)",
                  background: "rgba(99,102,241,0.05)",
                  color: "var(--text-secondary)",
                }
              : { color: "var(--faim-error-text)" }
          }
        >
          <span style={{ color: "#818cf8", fontWeight: 500 }}>
            Requested mode: {selectedModeLabel}
          </span>
          {" · "}Extractor: {selectedExtractorLabel}
          {" · "}
          {getProfileHelper(profile)} {getPersistHelper(persistMode)}{" "}
          {ingestModePolicy.supported
            ? "All profile/persist combinations supported by policy."
            : ingestModePolicy.reason}
        </div>

        {/* Pipeline bar */}
        <div
          className="flex items-center gap-0 border-t px-5 py-3"
          style={{ borderColor: "var(--os-stroke)" }}
        >
          {[
            {
              label: "queued",
              count: queueCounts.queued,
              active: queueCounts.queued > 0,
              color: "var(--text-tertiary)",
            },
            {
              label: "running",
              count: queueCounts.uploading + queueCounts.ingesting,
              active: true,
              color: "var(--faim-info-text)",
            },
            {
              label: "done",
              count: queueCounts.ingested + queueCounts.dedup_hit,
              active: true,
              color: "var(--faim-success-text)",
            },
          ].map((step, i) => (
            <span
              key={step.label}
              className="flex items-center gap-1.5 text-[11px]"
            >
              {i > 0 && (
                <span
                  className="mx-2 text-[10px]"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  →
                </span>
              )}
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{
                  background: step.count > 0 ? step.color : "var(--os-stroke)",
                }}
              />
              <span
                className="tabular-nums font-semibold"
                style={{ color: "var(--text-primary)" }}
              >
                {step.count}
              </span>
              <span style={{ color: "var(--text-tertiary)" }}>
                {step.label}
              </span>
            </span>
          ))}
          <span
            className="mx-3 h-3 w-px"
            style={{ background: "var(--os-stroke)" }}
          />
          <span className="flex items-center gap-1.5 text-[11px]">
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{
                background:
                  queueCounts.failed > 0
                    ? "var(--faim-error)"
                    : "var(--os-stroke)",
              }}
            />
            <span
              className="tabular-nums font-semibold"
              style={{
                color:
                  queueCounts.failed > 0
                    ? "var(--faim-error-text)"
                    : "var(--text-primary)",
              }}
            >
              {queueCounts.failed}
            </span>
            <span style={{ color: "var(--text-tertiary)" }}>failed</span>
          </span>
        </div>

        {/* Queue items */}
        <div className="border-t" style={{ borderColor: "var(--os-stroke)" }}>
          {queueItems.length === 0 ? (
            <div
              className="px-5 py-6 text-center text-xs"
              style={{ color: "var(--text-tertiary)" }}
            >
              No queued files yet. Drop files above to begin.
            </div>
          ) : (
            queueItems.map((item) => {
              const canCancel =
                !TERMINAL_QUEUE_STATUS.has(item.status) && !item.busyAction;
              const canRetry =
                (item.status === "failed" || item.status === "cancelled") &&
                !item.busyAction;
              const latest = latestMessage(item);
              const mode = modeSummary(item);

              return (
                <div
                  key={item.id}
                  className="overflow-hidden rounded-xl border p-4 transition-all"
                  style={{
                    borderColor: "var(--os-stroke)",
                    background: "var(--os-surface-2)",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
                  }}
                  data-testid="storage-queue-item"
                  data-filename={item.filename}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p
                          className="max-w-[320px] truncate text-sm font-medium"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {item.filename}
                        </p>
                        <Badge size="xs" variant={statusVariant(item.status)}>
                          {item.status}
                        </Badge>
                        {item.cancelRequested &&
                          !TERMINAL_QUEUE_STATUS.has(item.status) && (
                            <Badge size="xs" variant="warning">
                              cancel requested
                            </Badge>
                          )}
                      </div>
                      <p
                        className="mt-1 text-[11px]"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        {formatBytes(item.sizeBytes)} |{" "}
                        {item.mimeType || "application/octet-stream"} | job:{" "}
                        {shortId(item.jobId)} | raw: {shortId(item.rawId)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        size="xs"
                        variant="outline"
                        className="h-7"
                        data-testid="storage-queue-cancel"
                        data-filename={item.filename}
                        disabled={!canCancel}
                        onClick={() => {
                          void requestQueueCancel(item.id);
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="xs"
                        variant="outline"
                        className="h-7"
                        data-testid="storage-queue-retry"
                        data-filename={item.filename}
                        disabled={!canRetry || !ingestModePolicy.supported}
                        leftIcon={<RotateCcw size={12} />}
                        onClick={() => {
                          void retryQueueItem(item.id);
                        }}
                      >
                        Retry
                      </Button>
                      <Button
                        size="xs"
                        variant="ghost"
                        className="h-7"
                        onClick={() => removeQueueItem(item.id)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>

                  <div className="mt-2">
                    <Progress
                      value={item.progress}
                      showLabel
                      label="Lifecycle"
                      variant={
                        item.status === "failed" || item.status === "cancelled"
                          ? "error"
                          : "gradient"
                      }
                    />
                    {mode && (
                      <p
                        className="mt-1 text-[11px] text-cyan-300/90"
                        data-testid="storage-queue-mode"
                      >
                        {mode}
                      </p>
                    )}
                    <p
                      className="mt-1 text-[11px] text-slate-400"
                      data-testid="storage-queue-extractor"
                    >
                      Extractor:{" "}
                      {extractorModeLabel(
                        item.requestedExtractorMode ||
                          item.effectiveExtractorMode ||
                          extractorMode,
                      )}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-400">{latest}</p>
                  </div>

                  {!!item.events.length && (
                    <details
                      className="mt-3 rounded-lg border px-3 py-2 transition-all"
                      style={{
                        borderColor: "var(--os-stroke)",
                        background: "var(--os-surface-1)",
                      }}
                    >
                      <summary
                        className="cursor-pointer text-[11px] font-medium transition-colors hover:text-white"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        Timeline events ({item.events.length})
                      </summary>
                      <div className="mt-2 max-h-32 space-y-1.5 overflow-auto pr-1 text-[11px]">
                        {item.events.slice(-10).map((event) => (
                          <div
                            key={`${item.id}-${event.seq}`}
                            className="flex items-start justify-between gap-3"
                            style={{ color: "var(--text-secondary)" }}
                          >
                            <span className="min-w-0 flex-1 truncate opacity-90">
                              #{event.seq} {event.kind}
                            </span>
                            <span className="whitespace-nowrap opacity-50 font-mono">
                              {event.ts
                                ? new Date(event.ts).toLocaleTimeString()
                                : "-"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}

                  {item.error && (
                    <div className="mt-2 flex items-center gap-1 text-[11px] text-rose-400">
                      <XCircle size={12} /> {item.error}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ── File Catalog ─────────────────────────────────────── */}
      <div
        className="overflow-hidden rounded-xl border"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        {/* Header */}
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-1.5"
          style={{ borderColor: "var(--os-stroke)" }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-widest"
            style={{ color: "var(--text-tertiary)" }}
          >
            File Catalog
          </p>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {[
                { key: "postgres", label: "Postgres", ok: backends?.postgres },
                {
                  key: "raw_store",
                  label: "RawStore",
                  ok: backends?.raw_store,
                },
                { key: "redis", label: "Redis", ok: backends?.redis },
                { key: "qdrant", label: "Qdrant", ok: backends?.qdrant },
              ].map((b) => (
                <span
                  key={b.key}
                  className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-medium"
                  style={{
                    borderColor: b.ok
                      ? "rgba(52,211,153,0.25)"
                      : "rgba(248,113,113,0.25)",
                    background: b.ok
                      ? "rgba(52,211,153,0.08)"
                      : "rgba(248,113,113,0.08)",
                    color: b.ok
                      ? "var(--faim-success-text)"
                      : "var(--faim-error-text)",
                  }}
                >
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: "currentColor" }}
                  />
                  {b.label}
                </span>
              ))}
            </div>
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<RefreshCw size={12} />}
              onClick={() => {
                void refreshViews();
              }}
            >
              Refresh Catalog
            </Button>
          </div>
        </div>

        {/* Search + filter toolbar */}
        <div className="flex flex-wrap items-center gap-3 px-5 py-3">
          <div className="relative flex-1" style={{ maxWidth: 280 }}>
            <Search
              size={12}
              className="absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: "var(--text-tertiary)" }}
            />
            <input
              value={query}
              onChange={(e) => {
                setPage(0);
                setQuery(e.target.value);
              }}
              placeholder="Search filename or hash"
              className="h-8 w-full rounded-lg border pl-8 pr-3 text-xs outline-none transition-colors focus:border-indigo-500"
              style={{
                background: "var(--os-surface-2)",
                borderColor: "var(--os-stroke)",
                color: "var(--text-primary)",
              }}
            />
          </div>
          <ThemedSelect
            className="w-40"
            value={statusFilter}
            onChange={(val) => {
              setPage(0);
              setStatusFilter(val);
            }}
            options={[
              { value: "", label: "All statuses" },
              { value: "uploaded", label: "uploaded" },
              { value: "ingesting", label: "ingesting" },
              { value: "ingested", label: "ingested" },
              { value: "dedup_hit", label: "dedup_hit" },
              { value: "failed", label: "failed" },
              { value: "cancelled", label: "cancelled" },
              { value: "delete_requested", label: "delete_requested" },
            ]}
          />
        </div>

        {/* Table */}
        <div
          className="overflow-x-auto border-t"
          style={{ borderColor: "var(--os-stroke)" }}
        >
          <table className="w-full min-w-[960px] text-left">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--os-stroke)" }}>
                {[
                  "Filename",
                  "Status",
                  "Size",
                  "Raw ID",
                  "Updated",
                  "Actions",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2.5 text-[10px] font-medium uppercase tracking-wider whitespace-nowrap"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loadingFiles ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-xs"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    Loading storage catalog...
                  </td>
                </tr>
              ) : files.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-xs"
                    style={{ color: "var(--text-tertiary)" }}
                  >
                    No files found for current filters.
                  </td>
                </tr>
              ) : (
                files.map((row) => {
                  const busy = actionRawId === row.raw_id;
                  return (
                    <tr
                      key={row.raw_id}
                      className={`group transition-colors hover:bg-white/[0.02] ${rowAccent(row.ingest_status, row.delete_requested)}`}
                      style={{ borderBottom: "1px solid var(--os-stroke)" }}
                    >
                      <td className="px-4 py-3">
                        <div
                          className="max-w-[240px] truncate text-sm font-medium"
                          style={{ color: "var(--text-primary)" }}
                          title={row.filename}
                        >
                          {row.filename}
                        </div>
                        {row.error && (
                          <div
                            className="mt-0.5 flex items-center gap-1 text-[11px]"
                            style={{ color: "var(--faim-error-text)" }}
                          >
                            <XCircle size={11} /> {row.error}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          size="xs"
                          variant={statusVariant(row.ingest_status)}
                        >
                          {row.ingest_status}
                        </Badge>
                      </td>
                      <td
                        className="px-4 py-3 text-xs tabular-nums"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        {formatBytes(row.size_bytes)}
                      </td>
                      <td
                        className="px-4 py-3 font-mono text-[11px]"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        {shortId(row.raw_id)}
                      </td>
                      <td
                        className="px-4 py-3 text-xs whitespace-nowrap"
                        style={{ color: "var(--text-tertiary)" }}
                      >
                        {row.updated_at
                          ? new Date(row.updated_at).toLocaleString()
                          : "-"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                          <Button
                            size="xs"
                            variant="ghost"
                            className="h-6 text-[11px]"
                            data-testid="storage-file-inspect"
                            data-raw-id={row.raw_id}
                            disabled={busy || row.delete_requested}
                            leftIcon={<FileSearch size={11} />}
                            onClick={() => {
                              void openProvenance(row.raw_id, "faim");
                            }}
                          >
                            Inspect
                          </Button>
                          <Button
                            size="xs"
                            variant="ghost"
                            className="h-6 text-[11px]"
                            disabled={busy}
                            leftIcon={<Download size={11} />}
                            onClick={() => {
                              void downloadStorageFile(
                                row.raw_id,
                                row.filename,
                              );
                            }}
                          >
                            Download
                          </Button>
                          <Button
                            size="xs"
                            variant="ghost"
                            className="h-6 text-[11px]"
                            data-testid="storage-file-technical"
                            data-raw-id={row.raw_id}
                            disabled={busy || row.delete_requested}
                            leftIcon={<Activity size={11} />}
                            onClick={() => {
                              void openProvenance(row.raw_id, "technical");
                            }}
                          >
                            Technical Trace
                          </Button>
                          <Button
                            size="xs"
                            variant="ghost"
                            className="h-6 text-[11px]"
                            disabled={
                              busy ||
                              row.delete_requested ||
                              !ingestModePolicy.supported
                            }
                            onClick={() => {
                              void runFileAction(row.raw_id, "ingest");
                            }}
                          >
                            Re-ingest
                          </Button>
                          <Button
                            size="xs"
                            variant="ghost"
                            className="h-6 text-[11px]"
                            disabled={
                              busy ||
                              row.ingest_status !== "failed" ||
                              !ingestModePolicy.supported
                            }
                            leftIcon={<RotateCcw size={11} />}
                            onClick={() => {
                              void runFileAction(row.raw_id, "retry");
                            }}
                          >
                            Retry
                          </Button>
                          <Button
                            size="xs"
                            variant="danger"
                            className="h-6 text-[11px]"
                            disabled={busy || row.delete_requested}
                            onClick={() => {
                              void runFileAction(row.raw_id, "delete");
                            }}
                          >
                            Delete Req
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer / Pagination */}
        <div
          className="flex items-center justify-between border-t px-5 py-3 text-xs"
          style={{
            borderColor: "var(--os-stroke)",
            color: "var(--text-tertiary)",
          }}
        >
          <span>
            {loadingSummary ? "Loading..." : `Total ${total} file(s)`}
          </span>
          <div className="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="xs"
              className="h-6"
              disabled={page <= 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Prev
            </Button>
            <span
              className="px-2 tabular-nums"
              style={{ color: "var(--text-secondary)" }}
            >
              {Math.min(page + 1, totalPages)} / {totalPages}
            </span>
            <Button
              variant="ghost"
              size="xs"
              className="h-6"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </div>

      {supportedTypesOpen && (
        <div className="fixed inset-0 z-40">
          <button
            type="button"
            className="absolute inset-0 bg-black/45 backdrop-blur-sm"
            onClick={() => setSupportedTypesOpen(false)}
            aria-label="Close supported types panel"
          />

          <aside
            className="absolute right-0 top-0 h-full w-full max-w-[680px] overflow-y-auto border-l border-slate-700 bg-slate-950 p-5 shadow-2xl"
            data-testid="storage-supported-types-panel"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">
                  Supported Files Coverage
                </h3>
                <p className="text-xs text-slate-400">
                  Backend validator and extractor capability matrix
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="xs"
                  variant="outline"
                  onClick={() => {
                    void fetchSupportedTypesInternal();
                  }}
                >
                  Refresh
                </Button>
                <Button
                  size="icon-sm"
                  variant="ghost"
                  onClick={() => setSupportedTypesOpen(false)}
                  aria-label="Close"
                >
                  <X size={14} />
                </Button>
              </div>
            </div>

            {supportedTypesLoading && !supportedTypes ? (
              <div className="rounded-lg border border-slate-800 px-4 py-8 text-center text-sm text-slate-400">
                Loading supported type coverage...
              </div>
            ) : !supportedTypes ? (
              <div className="rounded-lg border border-slate-800 px-4 py-8 text-center text-sm text-slate-500">
                Supported coverage data is unavailable.
              </div>
            ) : (
              <div className="space-y-4">
                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">
                    Limits and OCR Policy
                  </h4>
                  <div className="grid grid-cols-1 gap-2 text-xs text-slate-300 sm:grid-cols-2">
                    <p>
                      <span className="text-slate-500">max batch total:</span>{" "}
                      {supportedTypes.max_batch_total_mb} MB
                    </p>
                    <p>
                      <span className="text-slate-500">file count:</span>{" "}
                      unlimited (total must be ≤{" "}
                      {supportedTypes.max_batch_total_mb} MB)
                    </p>
                    <p>
                      <span className="text-slate-500">extensions:</span>{" "}
                      {supportedTypes.total_extensions}
                    </p>
                    <p>
                      <span className="text-slate-500">MIME types:</span>{" "}
                      {supportedTypes.total_content_types}
                    </p>
                    <p>
                      <span className="text-slate-500">OCR enabled:</span>{" "}
                      {String(supportedTypes.ocr_enabled)}
                    </p>
                    <p>
                      <span className="text-slate-500">OCR engine:</span>{" "}
                      {supportedTypes.ocr_engine}
                    </p>
                    <p>
                      <span className="text-slate-500">OCR fail-closed:</span>{" "}
                      {String(supportedTypes.ocr_fail_closed)}
                    </p>
                  </div>
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">
                    Category Coverage
                  </h4>
                  <div className="space-y-2 text-xs">
                    {Object.entries(supportedTypes.categories).map(
                      ([category, extensions]) => (
                        <div
                          key={category}
                          className="rounded-lg border border-slate-800 px-2 py-2"
                        >
                          <p className="text-slate-300">
                            <span className="font-semibold">{category}</span>
                            <span className="ml-2 text-slate-500">
                              ({extensions.length})
                            </span>
                          </p>
                          <p className="mt-1 font-mono text-[11px] text-slate-400">
                            {extensions.join(", ") || "-"}
                          </p>
                        </div>
                      ),
                    )}
                  </div>
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">
                    Extractor Mapping
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                    {Object.entries(supportedTypes.extractor_doc_types).map(
                      ([docType, count]) => (
                        <div
                          key={docType}
                          className="rounded-md border border-slate-800 px-2 py-1"
                        >
                          <span className="font-mono">{docType}</span>: {count}
                        </div>
                      ),
                    )}
                  </div>
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">
                    OCR-Capable Extensions
                  </h4>
                  <p className="font-mono text-[11px] text-slate-400">
                    {supportedTypes.ocr_capable_extensions.join(", ") || "-"}
                  </p>
                </Card>
              </div>
            )}
          </aside>
        </div>
      )}

      <AnimatePresence>
        {provenanceOpen && (
          <div className="fixed inset-0 z-50 overflow-hidden">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 bg-black/5"
              onClick={() => setProvenanceOpen(false)}
              aria-label="Close provenance panel"
            />

            <motion.aside
              initial={{ x: "100%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "100%", opacity: 0 }}
              transition={{
                type: "spring",
                damping: 32,
                stiffness: 210,
                mass: 0.8,
              }}
              className="absolute right-4 top-4 bottom-4 w-full max-w-[720px] overflow-hidden border shadow-[0_30px_100px_rgba(0,0,0,0.7)] backdrop-blur-3xl"
              style={{
                borderColor: "rgba(255,255,255,0.12)",
                background: "rgba(10, 15, 25, 0.78)",
                borderRadius: "24px",
                boxShadow:
                  "0 25px 80px -20px rgba(0,0,0,0.9), inset 0 1px 1px rgba(255,255,255,0.08)",
              }}
              data-testid="storage-provenance-panel"
            >
              <div className="h-full w-full overflow-y-auto px-8 py-7 custom-scrollbar">
                <div
                  className="mb-6 flex items-center justify-between border-b pb-4"
                  style={{ borderColor: "var(--os-stroke)" }}
                >
                  <div>
                    <h3
                      className="text-base font-bold tracking-tight"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {provenanceView === "faim"
                        ? "FAIM Ingestion Dashboard"
                        : "Technical Audit Trace"}
                    </h3>
                    <p
                      className="text-[11px]"
                      style={{ color: "var(--text-tertiary)" }}
                    >
                      {provenanceView === "faim"
                        ? "Deterministic pipeline & fractal diagnostics"
                        : "Raw reference & node integration audit"}
                    </p>
                  </div>
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    onClick={() => setProvenanceOpen(false)}
                    aria-label="Close"
                    className="hover:rotate-90 transition-transform duration-300"
                  >
                    <X size={16} />
                  </Button>
                </div>

                {
                  (() => {
                    const data = provenanceData;
                    if (provenanceLoading) {
                      return (
                        <div
                          className="rounded-2xl border px-4 py-12 text-center text-xs"
                          style={{
                            borderColor: "var(--os-stroke)",
                            color: "var(--text-tertiary)",
                            background: "rgba(255,255,255,0.02)",
                          }}
                        >
                          <RefreshCw
                            className="inline-block animate-spin mr-2"
                            size={14}
                          />
                          Synchronizing provenance matrix...
                        </div>
                      );
                    }
                    if (!data) {
                      return (
                        <div
                          className="rounded-2xl border px-4 py-12 text-center text-xs"
                          style={{
                            borderColor: "var(--os-stroke)",
                            color: "var(--text-tertiary)",
                            background: "rgba(255,255,255,0.02)",
                          }}
                        >
                          No provenance sequence found for{" "}
                          <span
                            className="font-mono break-all"
                            style={{ color: "var(--faim-primary)" }}
                          >
                            {provenanceRawId}
                          </span>
                          .
                        </div>
                      );
                    }

                    return (
                      <div className="space-y-5">
                        {provenanceView === "faim" ? (
                          <>
                            <div
                              className="rounded-2xl border px-6 py-5"
                              style={{
                                background: "rgba(255,255,255,0.03)",
                                borderColor: "var(--os-stroke)",
                              }}
                            >
                              <p
                                className="mb-5 text-[10px] font-bold uppercase tracking-[0.2em]"
                                style={{ color: "var(--text-tertiary)" }}
                              >
                                Ingestion Pipeline Sequence
                              </p>
                              <div className="flex items-center gap-0">
                                {(() => {
                                  const kinds = new Set(
                                    data.events.map((e) => e.kind),
                                  );
                                  let curr = 1;
                                  if (
                                    kinds.has("WRITE_ATOMS_DONE") ||
                                    kinds.has("INGEST_DEDUP_HIT") ||
                                    data.file.ingest_status === "ingested" ||
                                    data.file.ingest_status === "dedup_hit"
                                  )
                                    curr = 5;
                                  else if (kinds.has("ENCODED")) curr = 4;
                                  else if (kinds.has("PACKET_CREATED"))
                                    curr = 3;
                                  else if (kinds.has("INGEST_START")) curr = 2;

                                  return [
                                    "Stored",
                                    "Perceived",
                                    "Packetized",
                                    "Encoded",
                                    "Integrated",
                                  ].map((label, i) => {
                                    const step = i + 1;
                                    const isDone = curr >= step;
                                    const isCurrent = curr === step;
                                    const color = isDone
                                      ? "var(--faim-success-text)"
                                      : "var(--os-stroke)";

                                    return (
                                      <span
                                        key={label}
                                        className="flex items-center gap-1.5 text-[11px]"
                                      >
                                        {i > 0 && (
                                          <span
                                            className="mx-2 text-[10px]"
                                            style={{
                                              color: "var(--text-tertiary)",
                                            }}
                                          >
                                            →
                                          </span>
                                        )}
                                        <span
                                          className="h-2 w-2 rounded-full"
                                          style={{
                                            background: isDone
                                              ? "currentColor"
                                              : "var(--os-stroke)",
                                            color: color,
                                            boxShadow: isCurrent
                                              ? "0 0 10px currentColor"
                                              : "none",
                                          }}
                                        />
                                        <span
                                          className="font-semibold"
                                          style={{
                                            color: isDone
                                              ? "var(--text-primary)"
                                              : "var(--text-tertiary)",
                                          }}
                                        >
                                          {label}
                                        </span>
                                      </span>
                                    );
                                  });
                                })()}
                              </div>
                            </div>

                            <div
                              className="rounded-2xl border px-6 py-5"
                              style={{
                                background: "rgba(255,255,255,0.03)",
                                borderColor: "var(--os-stroke)",
                              }}
                            >
                              <div className="mb-5 flex items-center justify-between">
                                <p
                                  className="text-[10px] font-bold uppercase tracking-[0.2em]"
                                  style={{ color: "var(--text-tertiary)" }}
                                >
                                  Fractal Diagnostics
                                </p>
                                <Badge
                                  variant="outline"
                                  className="text-[10px] px-2.5 py-0.5 h-5 uppercase font-black tracking-tighter"
                                  style={{
                                    borderColor: "rgba(52,211,153,0.3)",
                                    color: "var(--faim-success-text)",
                                    background: "rgba(52,211,153,0.05)",
                                  }}
                                >
                                  DETERMINISTIC
                                </Badge>
                              </div>

                              <div className="grid grid-cols-2 gap-6 text-xs">
                                <div>
                                  <p
                                    className="mb-1.5 text-[10px] uppercase tracking-wider font-medium"
                                    style={{ color: "var(--text-tertiary)" }}
                                  >
                                    Nodes / Dimension
                                  </p>
                                  <p
                                    className="font-mono text-sm font-bold"
                                    style={{ color: "var(--text-primary)" }}
                                  >
                                    {data.node_count}{" "}
                                    <span
                                      style={{
                                        color: "var(--text-tertiary)",
                                        fontSize: "11px",
                                        fontWeight: "normal",
                                      }}
                                    >
                                      /{" "}
                                      {data.events
                                        .find((e) => e.kind === "ENCODED")
                                        ?.payload_keys?.includes("vector_dim")
                                        ? "256"
                                        : "FAIM Standard"}
                                    </span>
                                  </p>
                                </div>
                                <div>
                                  <p
                                    className="mb-1.5 text-[10px] uppercase tracking-wider font-medium"
                                    style={{ color: "var(--text-tertiary)" }}
                                  >
                                    Method / Extractor
                                  </p>
                                  <p
                                    className="font-bold"
                                    style={{ color: "var(--text-primary)" }}
                                  >
                                    EvidenceBlocks (Native)
                                  </p>
                                  <p
                                    className="text-[10px] font-medium"
                                    style={{ color: "var(--text-tertiary)" }}
                                  >
                                    Non-LLM atomic extraction
                                  </p>
                                </div>

                                {data.dedup.dedup_record_found && (
                                  <div
                                    className="col-span-2 mt-2 rounded-xl border p-4"
                                    style={{
                                      background: "rgba(99,102,241,0.05)",
                                      borderColor: "rgba(99,102,241,0.15)",
                                    }}
                                  >
                                    <p
                                      className="mb-2 text-[9px] font-black uppercase tracking-[0.2em]"
                                      style={{ color: "#818cf8" }}
                                    >
                                      Idempotency Match
                                    </p>
                                    <p
                                      className="break-all font-mono text-[11px]"
                                      style={{ color: "var(--text-secondary)" }}
                                    >
                                      {data.dedup.packet_hash}
                                    </p>
                                  </div>
                                )}
                              </div>
                            </div>

                            <div
                              className="rounded-2xl border px-6 py-5"
                              style={{
                                background: "rgba(255,255,255,0.03)",
                                borderColor: "var(--os-stroke)",
                              }}
                            >
                              <p
                                className="mb-5 text-[10px] font-bold uppercase tracking-[0.2em]"
                                style={{ color: "var(--text-tertiary)" }}
                              >
                                Security & Sovereign Integrity
                              </p>

                              <div className="space-y-5">
                                <div>
                                  <p
                                    className="mb-2 text-[9px] font-medium uppercase tracking-[0.2em]"
                                    style={{ color: "var(--text-tertiary)" }}
                                  >
                                    SHA256 Fingerprint
                                  </p>
                                  <div
                                    className="flex items-center justify-between rounded-xl border p-3"
                                    style={{
                                      background: "rgba(0,0,0,0.2)",
                                      borderColor: "rgba(255,255,255,0.06)",
                                    }}
                                  >
                                    <p
                                      className="break-all font-mono text-[11px] font-medium"
                                      style={{ color: "var(--faim-primary)" }}
                                    >
                                      {data.file.sha256}
                                    </p>
                                    <Button
                                      variant="ghost"
                                      size="xs"
                                      className="h-7 w-7 p-0 ml-3"
                                      onClick={() => {
                                        void navigator.clipboard.writeText(
                                          data.file.sha256 || "",
                                        );
                                      }}
                                    >
                                      <FileText size={13} />
                                    </Button>
                                  </div>
                                </div>

                                <div className="grid grid-cols-2 gap-6">
                                  <div>
                                    <p
                                      className="mb-1 text-[9px] font-medium uppercase tracking-[0.2em]"
                                      style={{ color: "var(--text-tertiary)" }}
                                    >
                                      Raw Reference
                                    </p>
                                    <p
                                      className="font-mono text-[11px] font-bold break-all"
                                      style={{ color: "var(--text-secondary)" }}
                                    >
                                      {data.file.raw_id}
                                    </p>
                                  </div>
                                  <div>
                                    <p
                                      className="mb-1 text-[9px] font-medium uppercase tracking-[0.2em]"
                                      style={{ color: "var(--text-tertiary)" }}
                                    >
                                      Tenant Isolation
                                    </p>
                                    <div
                                      className="flex h-5 w-max items-center gap-1.5 rounded-full border px-3 text-[9px] font-black tracking-tight"
                                      style={{
                                        borderColor: "rgba(52,211,153,0.2)",
                                        background: "rgba(52,211,153,0.05)",
                                        color: "var(--faim-success-text)",
                                      }}
                                    >
                                      <ShieldCheck size={12} /> SECURE
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </>
                        ) : (
                          <div className="space-y-5">
                            <div
                              className="rounded-2xl border px-6 py-5"
                              style={{
                                background: "rgba(255,255,255,0.03)",
                                borderColor: "var(--os-stroke)",
                              }}
                            >
                              <p
                                className="mb-5 text-[10px] font-bold uppercase tracking-[0.2em]"
                                style={{ color: "var(--text-tertiary)" }}
                              >
                                Core Reference Metadata
                              </p>
                              <div className="grid grid-cols-2 gap-x-10 gap-y-5">
                                <div>
                                  <p
                                    className="mb-1.5 text-[9px] font-medium uppercase tracking-[0.2em]"
                                    style={{ color: "var(--text-tertiary)" }}
                                  >
                                    Filename
                                  </p>
                                  <p
                                    className="font-bold truncate text-sm"
                                    style={{ color: "var(--text-primary)" }}
                                  >
                                    {data.file.filename}
                                  </p>
                                </div>
                                <div className="col-span-2">
                                  <p
                                    className="mb-1.5 text-[9px] font-medium uppercase tracking-[0.2em]"
                                    style={{ color: "var(--text-tertiary)" }}
                                  >
                                    Raw ID
                                  </p>
                                  <p
                                    className="font-mono text-[11px] font-medium break-all"
                                    style={{ color: "var(--text-secondary)" }}
                                  >
                                    {data.file.raw_id}
                                  </p>
                                </div>
                              </div>
                            </div>

                            <div
                              className="rounded-2xl border px-6 py-5"
                              style={{
                                background: "rgba(255,255,255,0.03)",
                                borderColor: "var(--os-stroke)",
                              }}
                            >
                              <p
                                className="mb-5 text-[10px] font-bold uppercase tracking-[0.2em]"
                                style={{ color: "var(--text-tertiary)" }}
                              >
                                Raw Persistence Layer
                              </p>
                              <div className="grid grid-cols-2 gap-6">
                                <div>
                                  <p
                                    className="mb-1.5 text-[9px] font-medium uppercase tracking-[0.2em]"
                                    style={{ color: "var(--text-tertiary)" }}
                                  >
                                    Mime Type
                                  </p>
                                  <p
                                    className="text-[11px] font-mono font-bold"
                                    style={{ color: "var(--text-secondary)" }}
                                  >
                                    {data.file.mime_type || "unknown"}
                                  </p>
                                </div>
                                <div className="col-span-2">
                                  <p
                                    className="mb-1.5 text-[9px] font-medium uppercase tracking-[0.2em]"
                                    style={{ color: "var(--text-tertiary)" }}
                                  >
                                    Backend URI
                                  </p>
                                  <div
                                    className="rounded-xl border px-4 py-2 font-mono text-[11px] break-all shadow-inner"
                                    style={{
                                      background: "rgba(0,0,0,0.2)",
                                      borderColor: "rgba(255,255,255,0.06)",
                                      color: "var(--text-tertiary)",
                                    }}
                                  >
                                    {data.raw_ref?.uri || "no_uri_recorded"}
                                  </div>
                                </div>
                              </div>
                            </div>

                            <div
                              className="rounded-2xl border overflow-hidden"
                              style={{
                                background: "rgba(255,255,255,0.03)",
                                borderColor: "var(--os-stroke)",
                              }}
                            >
                              <div
                                className="flex items-center justify-between border-b px-6 py-4"
                                style={{
                                  borderColor: "rgba(255,255,255,0.06)",
                                }}
                              >
                                <p
                                  className="text-[10px] font-bold uppercase tracking-[0.2em]"
                                  style={{ color: "var(--text-tertiary)" }}
                                >
                                  Atomic Node Integration
                                </p>
                                <span
                                  className="text-[10px] font-black tracking-widest uppercase"
                                  style={{ color: "var(--text-tertiary)" }}
                                >
                                  {data.nodes.length} atoms
                                </span>
                              </div>
                              <div className="max-h-80 overflow-y-auto p-4 custom-scrollbar">
                                <div className="space-y-3">
                                  {data.nodes.length === 0 ? (
                                    <p
                                      className="py-8 text-center text-[11px] font-medium italic"
                                      style={{ color: "var(--text-tertiary)" }}
                                    >
                                      No nodes integrated yet.
                                    </p>
                                  ) : (
                                    data.nodes.map((n, i) => (
                                      <div
                                        key={i}
                                        className="flex flex-col gap-2 rounded-xl border px-5 py-4 shadow-sm"
                                        style={{
                                          background: "rgba(0,0,0,0.15)",
                                          borderColor: "rgba(255,255,255,0.04)",
                                        }}
                                      >
                                        <p
                                          className="font-mono text-[11px] font-black break-all"
                                          style={{
                                            color: "var(--text-secondary)",
                                          }}
                                        >
                                          {n.node_id}
                                        </p>
                                        <div className="flex items-center justify-between">
                                          <p
                                            className="text-[9px] uppercase tracking-tighter font-bold"
                                            style={{
                                              color: "var(--text-tertiary)",
                                            }}
                                          >
                                            VEC: {n.vector_hash?.slice(0, 16)}
                                            ... · BLK: {n.block_id || "-"}
                                          </p>
                                          <Badge
                                            variant="outline"
                                            className="h-4 text-[8px] border font-black opacity-60 px-1"
                                          >
                                            ATOM
                                          </Badge>
                                        </div>
                                      </div>
                                    ))
                                  )}
                                </div>
                              </div>
                            </div>

                            <div
                              className="rounded-2xl border overflow-hidden"
                              style={{
                                background: "rgba(255,255,255,0.03)",
                                borderColor: "var(--os-stroke)",
                              }}
                            >
                              <div
                                className="flex items-center justify-between border-b px-6 py-4"
                                style={{
                                  borderColor: "rgba(255,255,255,0.06)",
                                }}
                              >
                                <p
                                  className="text-[10px] font-bold uppercase tracking-[0.2em]"
                                  style={{ color: "var(--text-tertiary)" }}
                                >
                                  Sequential Event Stream
                                </p>
                                <span
                                  className="text-[10px] font-black tracking-widest uppercase"
                                  style={{ color: "var(--text-tertiary)" }}
                                >
                                  {data.events.length} signals
                                </span>
                              </div>
                              <div className="p-6 relative">
                                <div
                                  className="absolute left-7 top-8 bottom-8 w-px"
                                  style={{
                                    background: "rgba(255,255,255,0.06)",
                                  }}
                                />
                                <div className="space-y-6 relative z-10">
                                  {data.events.length === 0 ? (
                                    <p
                                      className="text-[11px] font-medium italic"
                                      style={{ color: "var(--text-tertiary)" }}
                                    >
                                      No trace signals recorded.
                                    </p>
                                  ) : (
                                    data.events.map((e, i) => (
                                      <div
                                        key={i}
                                        className="flex gap-4 text-[11px] group"
                                      >
                                        <div
                                          className="w-2 h-2 rounded-full mt-1.5 shrink-0 transition-transform group-hover:scale-125 bg-[var(--faim-primary)]"
                                          style={{
                                            boxShadow: `0 0 8px var(--faim-primary)`,
                                          }}
                                        />
                                        <div className="flex-1 min-w-0">
                                          <p
                                            className="font-black uppercase tracking-widest text-[10px]"
                                            style={{
                                              color: "var(--text-primary)",
                                            }}
                                          >
                                            {e.kind}
                                          </p>
                                          <p
                                            className="text-[9px] mt-1 font-mono font-medium opacity-60"
                                            style={{
                                              color: "var(--text-tertiary)",
                                            }}
                                          >
                                            TS:{" "}
                                            {e.ts
                                              ? new Date(e.ts).toISOString()
                                              : "-"}
                                          </p>
                                          {Object.keys(e.payload || {}).length >
                                            0 && (
                                            <div className="mt-2 flex flex-wrap gap-1.5">
                                              {Object.entries(e.payload)
                                                .slice(0, 4)
                                                .map(([key, value]) => (
                                                  <span
                                                    key={`${e.seq}-${key}`}
                                                    className="rounded-full border px-2 py-0.5 font-mono text-[9px]"
                                                    style={{
                                                      borderColor:
                                                        "rgba(255,255,255,0.08)",
                                                      background:
                                                        "rgba(255,255,255,0.03)",
                                                      color:
                                                        "var(--text-secondary)",
                                                    }}
                                                  >
                                                    {key}:{" "}
                                                    {typeof value === "string"
                                                      ? value
                                                      : JSON.stringify(value)}
                                                  </span>
                                                ))}
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    ))
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })() as React.ReactNode
                }
              </div>
            </motion.aside>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
