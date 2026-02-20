"use client";

import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileSearch,
  FileText,
  HardDrive,
  RefreshCw,
  RotateCcw,
  Search,
  Shield,
  UploadCloud,
  X,
  XCircle,
} from "lucide-react";
import { getSession, useSession } from "next-auth/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Badge, Button, Card, Input, Progress, useToast } from "@/components/ui";
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
  effective_profile?: string | null;
  effective_persist_mode?: string | null;
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
  effective_profile?: string | null;
  effective_persist_mode?: string | null;
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
  effective_profile?: string | null;
  effective_persist_mode?: string | null;
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
    effective_profile?: string | null;
    effective_persist_mode?: string | null;
    durability_path?: string | null;
  };
};

type StorageSupportedTypesResponse = {
  max_upload_size_bytes: number;
  max_upload_size_mb: number;
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

type QueueItem = {
  id: string;
  file: File;
  filename: string;
  sizeBytes: number;
  mimeType: string;
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
  effectiveProfile?: string | null;
  effectivePersistMode?: string | null;
  durabilityPath?: string | null;
};

const PAGE_SIZE = 20;
const MAX_UPLOAD_CONCURRENCY = 3;
const MAX_QUEUE_ITEMS = 120;
const MAX_QUEUE_EVENTS = 60;
const JOB_POLL_INTERVAL_MS = 1800;
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
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exp);
  return `${value.toFixed(value >= 100 || exp === 0 ? 0 : 1)} ${units[exp]}`;
}

function statusVariant(status: string): "default" | "success" | "warning" | "error" | "info" {
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
  if (normalized === "ingested" || normalized === "completed") return "ingested";
  if (normalized === "dedup_hit") return "dedup_hit";
  if (normalized === "failed" || normalized === "error") return "failed";
  if (normalized === "cancelled") return "cancelled";
  if (normalized === "ingesting" || normalized === "running" || normalized === "pending") {
    return "ingesting";
  }
  if (normalized === "uploading" || normalized === "uploaded") return "uploading";
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

  const message = typeof last.payload?.message === "string" ? String(last.payload.message) : "";
  const status = typeof last.payload?.status === "string" ? String(last.payload.status) : "";

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
    item.durabilityPath
  );
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
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
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
  const { data: session } = useSession();
  const { toast } = useToast();

  const graphId = (session as { graphId?: string } | null)?.graphId || "default";

  const [files, setFiles] = useState<StorageFileItem[]>([]);
  const [summary, setSummary] = useState<StorageSummary | null>(null);
  const [backends, setBackends] = useState<StorageBackends | null>(null);
  const [supportedTypes, setSupportedTypes] = useState<StorageSupportedTypesResponse | null>(null);
  const [total, setTotal] = useState(0);

  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const [loadingFiles, setLoadingFiles] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [actionRawId, setActionRawId] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [profile, setProfile] = useState("strict");
  const [persistMode, setPersistMode] = useState("relaxed");

  const ingestModePolicy = useMemo(
    () => resolveUiModePolicy("ingest", profile, persistMode),
    [persistMode, profile]
  );
  const selectedModeLabel = useMemo(
    () => formatModePair(profile, persistMode),
    [persistMode, profile]
  );

  const [provenanceOpen, setProvenanceOpen] = useState(false);
  const [provenanceLoading, setProvenanceLoading] = useState(false);
  const [provenanceRawId, setProvenanceRawId] = useState<string | null>(null);
  const [provenanceData, setProvenanceData] = useState<StorageProvenanceResponse | null>(null);
  const [supportedTypesOpen, setSupportedTypesOpen] = useState(false);
  const [supportedTypesLoading, setSupportedTypesLoading] = useState(false);

  const queueRef = useRef<QueueItem[]>([]);
  const uploadControllersRef = useRef<Map<string, AbortController>>(new Map());
  const refreshLockRef = useRef(false);

  useEffect(() => {
    queueRef.current = queueItems;
  }, [queueItems]);

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

  async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
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
      throw new ApiError(response.status, normalizeApiError(payload, `Request failed (${response.status})`));
    }

    return (payload as T) || ({} as T);
  }

  const fetchFilesInternal = useCallback(async () => {
    setLoadingFiles(true);
    try {
      const params = new URLSearchParams({
        graph_id: graphId,
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });
      if (statusFilter) params.set("status", statusFilter);
      if (query.trim()) params.set("q", query.trim());

      const data = await fetchJson<FileListResponse>(`/api/v1/storage/files?${params.toString()}`);
      setFiles(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error("Failed to load storage files", message);
    } finally {
      setLoadingFiles(false);
    }
  }, [graphId, page, query, statusFilter, toast]);

  const fetchSummaryInternal = useCallback(async () => {
    setLoadingSummary(true);
    try {
      const [summaryData, backendData] = await Promise.all([
        fetchJson<StorageSummary>(`/api/v1/storage/summary?graph_id=${encodeURIComponent(graphId)}`),
        fetchJson<StorageBackends>(`/api/v1/storage/backends/health`),
      ]);
      setSummary(summaryData);
      setBackends(backendData);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.warning("Storage summary unavailable", message);
    } finally {
      setLoadingSummary(false);
    }
  }, [graphId, toast]);

  const fetchSupportedTypesInternal = useCallback(async () => {
    setSupportedTypesLoading(true);
    try {
      const data = await fetchJson<StorageSupportedTypesResponse>(`/api/v1/storage/supported-types`);
      setSupportedTypes(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.warning("Supported file coverage unavailable", message);
    } finally {
      setSupportedTypesLoading(false);
    }
  }, [toast]);

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
      await Promise.all([fetchFilesInternal(), fetchSummaryInternal()]);
    } finally {
      refreshLockRef.current = false;
    }
  }, [fetchFilesInternal, fetchSummaryInternal]);

  const patchQueueItem = useCallback(
    (itemId: string, updater: (item: QueueItem) => QueueItem) => {
      setQueueItems((prev) => prev.map((item) => (item.id === itemId ? updater(item) : item)));
    },
    []
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
        const latestSeq = trimmed.length ? trimmed[trimmed.length - 1].seq : current.lastEventSeq;
        return {
          ...current,
          events: trimmed,
          lastEventSeq: Math.max(current.lastEventSeq, latestSeq),
          updatedAt: safeNow(),
        };
      });
    },
    [patchQueueItem]
  );

  const refreshQueueJob = useCallback(
    async (itemId: string, jobId: string) => {
      const current = queueRef.current.find((item) => item.id === itemId);
      if (!current || TERMINAL_QUEUE_STATUS.has(current.status)) return;

      try {
        const [statusData, eventsData] = await Promise.all([
          fetchJson<UploadStatusResponse>(`/api/v1/storage/uploads/${encodeURIComponent(jobId)}`),
          fetchJson<StorageJobEventsResponse>(`/api/v1/storage/uploads/${encodeURIComponent(jobId)}/events`),
        ]);

        const fileMatch =
          statusData.files.find((row) => (current.rawId ? row.raw_id === current.rawId : row.filename === current.filename)) ||
          statusData.files[0];

        const nextEvents = (eventsData.events || []).filter((event) => event.seq > current.lastEventSeq);
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
          requestedProfile: statusData.requested_profile ?? item.requestedProfile,
          requestedPersistMode:
            statusData.requested_persist_mode ?? item.requestedPersistMode,
          effectiveProfile: statusData.effective_profile ?? item.effectiveProfile,
          effectivePersistMode:
            statusData.effective_persist_mode ?? item.effectivePersistMode,
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

        const message = error instanceof Error ? error.message : "Unknown error";
        patchQueueItem(itemId, (item) => ({
          ...item,
          error: message,
          updatedAt: safeNow(),
        }));
      }
    },
    [appendQueueEvents, patchQueueItem, refreshViews]
  );

  const enqueueFiles = useCallback(
    (incomingFiles: File[]) => {
      const modePolicy = resolveUiModePolicy("ingest", profile, persistMode);
      if (!modePolicy.supported) {
        toast.warning(
          "Unsupported mode combination",
          modePolicy.reason || "Choose a supported profile/persist mode."
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
        });
      }

      if (rejected.length) {
        toast.warning(
          "Some files were rejected",
          `${rejected.length} file(s) missing required client metadata (name/type/size)`
        );
      }

      if (!accepted.length) return;

      setQueueItems((prev) => trimQueue([...prev, ...accepted]));
    },
    [persistMode, profile, toast]
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
          error: modePolicy.reason || "Selected profile/persist mode is not allowed.",
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
        formData.set("graph_id", graphId);
        formData.set("profile", profile);
        formData.set("persist_mode", persistMode);
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
          throw new ApiError(response.status, normalizeApiError(payload, "Upload failed"));
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
          effectiveProfile:
            result?.effective_profile ??
            batch.effective_profile ??
            item.effectiveProfile,
          effectivePersistMode:
            result?.effective_persist_mode ??
            batch.effective_persist_mode ??
            item.effectivePersistMode,
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

        const message = error instanceof Error ? error.message : "Unknown error";
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
    [graphId, patchQueueItem, persistMode, profile, refreshQueueJob, refreshViews]
  );

  const requestQueueCancel = useCallback(
    async (itemId: string) => {
      const current = queueRef.current.find((item) => item.id === itemId);
      if (!current || TERMINAL_QUEUE_STATUS.has(current.status) || current.busyAction) return;

      patchQueueItem(itemId, (item) => ({ ...item, busyAction: "cancel", updatedAt: safeNow() }));

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
            { method: "POST" }
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
        const message = error instanceof Error ? error.message : "Unknown error";
        patchQueueItem(itemId, (item) => ({
          ...item,
          busyAction: undefined,
          error: message,
          updatedAt: safeNow(),
        }));
      }
    },
    [patchQueueItem, refreshViews]
  );

  const retryQueueItem = useCallback(
    async (itemId: string) => {
      const current = queueRef.current.find((item) => item.id === itemId);
      if (!current || current.busyAction) return;
      if (!(current.status === "failed" || current.status === "cancelled")) return;
      const modePolicy = resolveUiModePolicy("ingest", profile, persistMode);
      if (!modePolicy.supported) {
        toast.warning("Unsupported mode combination", modePolicy.reason || "Choose a supported profile/persist mode.");
        return;
      }

      patchQueueItem(itemId, (item) => ({ ...item, busyAction: "retry", updatedAt: safeNow() }));

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
            effectiveProfile: undefined,
            effectivePersistMode: undefined,
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
          `/api/v1/storage/files/${encodeURIComponent(current.rawId)}/retry?graph_id=${encodeURIComponent(graphId)}&profile=${encodeURIComponent(profile)}&persist_mode=${encodeURIComponent(persistMode)}`,
          { method: "POST" }
        );

        const status = mapStorageStatus(data.ingest?.status || data.file?.ingest_status || data.status);

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
          effectiveProfile:
            data.ingest?.effective_profile ?? item.effectiveProfile,
          effectivePersistMode:
            data.ingest?.effective_persist_mode ?? item.effectivePersistMode,
          durabilityPath: data.ingest?.durability_path ?? item.durabilityPath,
          error: data.ingest?.error || data.file?.error || undefined,
          busyAction: undefined,
          updatedAt: safeNow(),
        }));

        await refreshViews();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
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
    [graphId, patchQueueItem, persistMode, profile, refreshViews, toast]
  );

  const clearTerminalQueueItems = useCallback(() => {
    setQueueItems((prev) => prev.filter((item) => !TERMINAL_QUEUE_STATUS.has(item.status)));
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
            modePolicy.reason || "Choose a supported profile/persist mode."
          );
          return;
        }
      }
      setActionRawId(rawId);
      try {
        let url = `/api/v1/storage/files/${encodeURIComponent(rawId)}`;
        let method = "POST";

        if (action === "ingest") {
          url += `/ingest?graph_id=${encodeURIComponent(graphId)}&profile=${encodeURIComponent(profile)}&persist_mode=${encodeURIComponent(persistMode)}`;
        } else if (action === "retry") {
          url += `/retry?graph_id=${encodeURIComponent(graphId)}&profile=${encodeURIComponent(profile)}&persist_mode=${encodeURIComponent(persistMode)}`;
        } else {
          method = "DELETE";
          url += `?graph_id=${encodeURIComponent(graphId)}&reason=${encodeURIComponent("Requested from storage UI")}`;
        }

        const data = await fetchJson<StorageIngestActionResponse | unknown>(url, { method });
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
              ingestData.durability_path
            )
          : null;

        if (action === "delete") {
          toast.info("Delete request submitted", "File marked as delete_requested");
        } else if (action === "retry") {
          toast.success("Retry completed", modeText || "File reprocessed");
        } else {
          toast.success("Re-ingest completed", modeText || "File reprocessed");
        }

        await refreshViews();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        toast.error(`Failed to ${action}`, message);
      } finally {
        setActionRawId(null);
      }
    },
    [graphId, persistMode, profile, refreshViews, toast]
  );

  const openProvenance = useCallback(
    async (rawId: string) => {
      setProvenanceOpen(true);
      setProvenanceRawId(rawId);
      setProvenanceLoading(true);
      setProvenanceData(null);

      try {
        const data = await fetchJson<StorageProvenanceResponse>(
          `/api/v1/storage/files/${encodeURIComponent(rawId)}/provenance?graph_id=${encodeURIComponent(graphId)}`
        );
        setProvenanceData(data);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        toast.error("Failed to load provenance", message);
      } finally {
        setProvenanceLoading(false);
      }
    },
    [graphId, toast]
  );

  useEffect(() => {
    fetchFilesInternal();
  }, [fetchFilesInternal]);

  useEffect(() => {
    fetchSummaryInternal();
  }, [fetchSummaryInternal]);

  useEffect(() => {
    void fetchSupportedTypesInternal();
  }, [fetchSupportedTypesInternal]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      fetchSummaryInternal();
    }, 15000);
    return () => window.clearInterval(interval);
  }, [fetchSummaryInternal]);

  useEffect(() => {
    const activeUploads = queueItems.filter((item) => item.status === "uploading" || item.status === "ingesting").length;
    const capacity = MAX_UPLOAD_CONCURRENCY - activeUploads;
    if (capacity <= 0) return;

    const queued = queueItems.filter((item) => item.status === "queued").slice(0, capacity);
    for (const item of queued) {
      void startQueueUpload(item.id);
    }
  }, [queueItems, startQueueUpload]);

  useEffect(() => {
    const pollTargets = queueItems.filter(
      (item) => item.jobId && !TERMINAL_QUEUE_STATUS.has(item.status)
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
  }, [queueItems, refreshQueueJob]);

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
    [enqueueFiles]
  );

  const onDropFiles = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragOver(false);
      const dropped = Array.from(event.dataTransfer.files || []);
      enqueueFiles(dropped);
    },
    [enqueueFiles]
  );

  const ingestedCount = summary?.by_status?.ingested || 0;
  const failedCount = summary?.by_status?.failed || 0;
  const dedupCount = summary?.by_status?.dedup_hit || 0;

  return (
    <div className="space-y-6 pb-8 text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold" data-testid="storage-page-title">
            Storage Control Plane
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Multi-file upload queue, ingest lifecycle tracking, and immutable provenance for graph `{graphId}`.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          leftIcon={<RefreshCw size={14} />}
          onClick={() => {
            void refreshViews();
          }}
        >
          Refresh
        </Button>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="os-card rounded-2xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Total Files</p>
              <p className="mt-1 text-2xl font-semibold">{summary?.total_files ?? 0}</p>
            </div>
            <FileText className="text-cyan-400" size={20} />
          </div>
        </Card>
        <Card className="os-card rounded-2xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Stored Bytes</p>
              <p className="mt-1 text-2xl font-semibold">{formatBytes(summary?.total_bytes ?? 0)}</p>
            </div>
            <HardDrive className="text-violet-400" size={20} />
          </div>
        </Card>
        <Card className="os-card rounded-2xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Ingested</p>
              <p className="mt-1 text-2xl font-semibold">{ingestedCount}</p>
              <p className="text-xs text-slate-500">Dedup hits: {dedupCount}</p>
            </div>
            <CheckCircle2 className="text-emerald-400" size={20} />
          </div>
        </Card>
        <Card className="os-card rounded-2xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Failures</p>
              <p className="mt-1 text-2xl font-semibold">{failedCount}</p>
              <p className="text-xs text-slate-500">Needs retry</p>
            </div>
            <AlertCircle className="text-rose-400" size={20} />
          </div>
        </Card>
      </div>

      <Card className="os-card rounded-2xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Upload Panel</h2>
            <p className="text-xs text-slate-400">Drag-drop or select files. Each file runs as its own upload job for per-file control.</p>
          </div>
          <div className="flex items-center gap-2">
            <label
              className={`inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs ${
                ingestModePolicy.supported
                  ? "cursor-pointer hover:bg-slate-900/40"
                  : "cursor-not-allowed opacity-50"
              }`}
            >
              <UploadCloud size={14} />
              Add Files
              <input
                type="file"
                multiple
                className="hidden"
                onChange={onInputFiles}
                disabled={!ingestModePolicy.supported}
              />
            </label>
            <Button
              size="sm"
              variant="outline"
              leftIcon={<FileText size={14} />}
              data-testid="storage-supported-types-open"
              onClick={openSupportedTypes}
            >
              Supported Files
              {supportedTypes ? ` (${supportedTypes.total_extensions})` : ""}
            </Button>
            <Button size="sm" variant="outline" onClick={clearTerminalQueueItems}>
              Clear Completed
            </Button>
          </div>
        </div>

        <div
          className={`rounded-xl border border-dashed p-5 transition ${
            isDragOver
              ? "border-cyan-400 bg-cyan-500/10"
              : "border-slate-700 bg-slate-950/40"
          }`}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={onDropFiles}
        >
          <div className="flex flex-col items-center justify-center gap-1 text-center">
            <UploadCloud className="text-cyan-400" size={20} />
            <p className="text-sm text-slate-200">Drop files here</p>
            <p className="text-xs text-slate-400">Multi-file add is append-only. Queue keeps current in-flight work.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs text-slate-400">Profile</label>
            <select
              value={profile}
              onChange={(e) => setProfile(e.target.value)}
              className="h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm"
            >
              <option value="strict">strict</option>
              <option value="fast">fast</option>
              <option value="relaxed">relaxed</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">Persist Mode</label>
            <select
              value={persistMode}
              onChange={(e) => setPersistMode(e.target.value)}
              className="h-9 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm"
            >
              <option value="relaxed">relaxed</option>
              <option value="strict">strict</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">Queue Depth</label>
            <div className="h-9 rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm leading-9 text-slate-300">
              {queueItems.length} item(s)
            </div>
          </div>
        </div>

        <div
          className={`rounded-lg border p-3 text-xs ${
            ingestModePolicy.supported
              ? "border-slate-800 bg-slate-950/40 text-slate-400"
              : "border-rose-400/35 bg-rose-500/10 text-rose-200"
          }`}
        >
          <p className="font-medium text-slate-300">
            Requested mode: <span className="font-mono">{selectedModeLabel}</span>
          </p>
          <p className="mt-1">{getProfileHelper(profile)}</p>
          <p>{getPersistHelper(persistMode)}</p>
          <p className="mt-1">
            {ingestModePolicy.supported
              ? "All profile/persist combinations are currently supported by policy."
              : ingestModePolicy.reason || "Selected profile/persist combination is not supported."}
          </p>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <Badge size="xs" variant="default">queued: {queueCounts.queued}</Badge>
            <Badge size="xs" variant="info">running: {queueCounts.uploading + queueCounts.ingesting}</Badge>
            <Badge size="xs" variant="success">done: {queueCounts.ingested + queueCounts.dedup_hit}</Badge>
            <Badge size="xs" variant="error">failed: {queueCounts.failed}</Badge>
            <Badge size="xs" variant="warning">cancelled: {queueCounts.cancelled}</Badge>
          </div>

          <div className="max-h-[420px] space-y-2 overflow-auto pr-1">
            {queueItems.length === 0 ? (
              <div className="rounded-md border border-slate-800 px-3 py-5 text-center text-xs text-slate-500">
                No queued files yet.
              </div>
            ) : (
              queueItems.map((item) => {
                const canCancel = !TERMINAL_QUEUE_STATUS.has(item.status) && !item.busyAction;
                const canRetry = (item.status === "failed" || item.status === "cancelled") && !item.busyAction;
                const latest = latestMessage(item);
                const mode = modeSummary(item);

                return (
                  <div
                    key={item.id}
                    className="rounded-lg border border-slate-800 bg-slate-950/60 p-3"
                    data-testid="storage-queue-item"
                    data-filename={item.filename}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="max-w-[320px] truncate text-sm text-slate-200">{item.filename}</p>
                          <Badge size="xs" variant={statusVariant(item.status)}>
                            {item.status}
                          </Badge>
                          {item.cancelRequested && !TERMINAL_QUEUE_STATUS.has(item.status) && (
                            <Badge size="xs" variant="warning">cancel requested</Badge>
                          )}
                        </div>
                        <p className="mt-0.5 text-[11px] text-slate-500">
                          {formatBytes(item.sizeBytes)} | {item.mimeType || "application/octet-stream"} | job: {shortId(item.jobId)} | raw: {shortId(item.rawId)}
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
                        variant={item.status === "failed" || item.status === "cancelled" ? "error" : "gradient"}
                      />
                      {mode && (
                        <p className="mt-1 text-[11px] text-cyan-300/90" data-testid="storage-queue-mode">
                          {mode}
                        </p>
                      )}
                      <p className="mt-1 text-[11px] text-slate-400">{latest}</p>
                    </div>

                    {!!item.events.length && (
                      <details className="mt-2 rounded-md border border-slate-800 bg-slate-950/30 px-2 py-1">
                        <summary className="cursor-pointer text-[11px] text-slate-400">
                          Timeline events ({item.events.length})
                        </summary>
                        <div className="mt-1 max-h-28 space-y-1 overflow-auto text-[11px]">
                          {item.events.slice(-8).map((event) => (
                            <div key={`${item.id}-${event.seq}`} className="flex items-start justify-between gap-2 text-slate-300">
                              <span className="min-w-0 flex-1 truncate">#{event.seq} {event.kind}</span>
                              <span className="whitespace-nowrap text-slate-500">
                                {event.ts ? new Date(event.ts).toLocaleTimeString() : "-"}
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
      </Card>

      <Card className="os-card rounded-2xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">File Catalog</h2>
            <p className="text-xs text-slate-400">Immutable raw files and ingest lifecycle status.</p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <Badge size="xs" variant={backends?.postgres ? "success" : "error"}>
              <Database size={12} /> Postgres
            </Badge>
            <Badge size="xs" variant={backends?.raw_store ? "success" : "error"}>
              <HardDrive size={12} /> RawStore
            </Badge>
            <Badge size="xs" variant={backends?.redis ? "success" : "warning"}>
              <Shield size={12} /> Redis
            </Badge>
            <Badge size="xs" variant={backends?.qdrant ? "success" : "warning"}>
              <Shield size={12} /> Qdrant
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Input
            value={query}
            onChange={(event) => {
              setPage(0);
              setQuery(event.target.value);
            }}
            placeholder="Search filename or hash"
            leftIcon={<Search size={14} />}
          />
          <select
            value={statusFilter}
            onChange={(event) => {
              setPage(0);
              setStatusFilter(event.target.value);
            }}
            className="h-9 rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm"
          >
            <option value="">All statuses</option>
            <option value="uploaded">uploaded</option>
            <option value="ingesting">ingesting</option>
            <option value="ingested">ingested</option>
            <option value="dedup_hit">dedup_hit</option>
            <option value="failed">failed</option>
            <option value="cancelled">cancelled</option>
            <option value="delete_requested">delete_requested</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={() => {
              void refreshViews();
            }}
          >
            Refresh Catalog
          </Button>
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full min-w-[1040px] text-left text-xs">
            <thead className="bg-slate-900/50 text-slate-400">
              <tr>
                <th className="px-3 py-2 font-medium">Filename</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Size</th>
                <th className="px-3 py-2 font-medium">Raw ID</th>
                <th className="px-3 py-2 font-medium">Updated</th>
                <th className="px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loadingFiles ? (
                <tr>
                  <td colSpan={6} className="px-3 py-10 text-center text-slate-500">
                    Loading storage catalog...
                  </td>
                </tr>
              ) : files.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-10 text-center text-slate-500">
                    No files found for current filters.
                  </td>
                </tr>
              ) : (
                files.map((row) => {
                  const busy = actionRawId === row.raw_id;
                  return (
                    <tr key={row.raw_id} className="border-t border-slate-800/80">
                      <td className="px-3 py-2">
                        <div className="max-w-[280px] truncate text-slate-200">{row.filename}</div>
                        {row.error && (
                          <div className="mt-0.5 flex items-center gap-1 text-[11px] text-rose-400">
                            <XCircle size={12} /> {row.error}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <Badge size="xs" variant={statusVariant(row.ingest_status)}>
                          {row.ingest_status}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-slate-300">{formatBytes(row.size_bytes)}</td>
                      <td className="px-3 py-2 font-mono text-[11px] text-slate-400">{shortId(row.raw_id)}</td>
                      <td className="px-3 py-2 text-slate-400">
                        {row.updated_at ? new Date(row.updated_at).toLocaleString() : "-"}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-1">
                          <Button
                            size="xs"
                            variant="outline"
                            className="h-7"
                            data-testid="storage-file-inspect"
                            data-raw-id={row.raw_id}
                            disabled={busy || row.delete_requested}
                            leftIcon={<FileSearch size={12} />}
                            onClick={() => {
                              void openProvenance(row.raw_id);
                            }}
                          >
                            Inspect
                          </Button>
                          <Button
                            size="xs"
                            variant="outline"
                            className="h-7"
                            disabled={
                              busy || row.delete_requested || !ingestModePolicy.supported
                            }
                            onClick={() => {
                              void runFileAction(row.raw_id, "ingest");
                            }}
                          >
                            Re-ingest
                          </Button>
                          <Button
                            size="xs"
                            variant="outline"
                            className="h-7"
                            disabled={
                              busy ||
                              row.ingest_status !== "failed" ||
                              !ingestModePolicy.supported
                            }
                            leftIcon={<RotateCcw size={12} />}
                            onClick={() => {
                              void runFileAction(row.raw_id, "retry");
                            }}
                          >
                            Retry
                          </Button>
                          <Button
                            size="xs"
                            variant="danger"
                            className="h-7"
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

        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{loadingSummary ? "Loading summary..." : `Total ${total} file(s)`}</span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="xs"
              className="h-7"
              disabled={page <= 0}
              onClick={() => setPage((prev) => Math.max(0, prev - 1))}
            >
              Prev
            </Button>
            <span>
              Page {Math.min(page + 1, totalPages)} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="xs"
              className="h-7"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((prev) => prev + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>

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
                <h3 className="text-sm font-semibold">Supported Files Coverage</h3>
                <p className="text-xs text-slate-400">Backend validator and extractor capability matrix</p>
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
                  <h4 className="text-xs font-semibold text-slate-300">Limits and OCR Policy</h4>
                  <div className="grid grid-cols-1 gap-2 text-xs text-slate-300 sm:grid-cols-2">
                    <p><span className="text-slate-500">max upload:</span> {supportedTypes.max_upload_size_mb} MB</p>
                    <p><span className="text-slate-500">extensions:</span> {supportedTypes.total_extensions}</p>
                    <p><span className="text-slate-500">MIME types:</span> {supportedTypes.total_content_types}</p>
                    <p><span className="text-slate-500">OCR enabled:</span> {String(supportedTypes.ocr_enabled)}</p>
                    <p><span className="text-slate-500">OCR engine:</span> {supportedTypes.ocr_engine}</p>
                    <p><span className="text-slate-500">OCR fail-closed:</span> {String(supportedTypes.ocr_fail_closed)}</p>
                  </div>
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">Category Coverage</h4>
                  <div className="space-y-2 text-xs">
                    {Object.entries(supportedTypes.categories).map(([category, extensions]) => (
                      <div key={category} className="rounded-lg border border-slate-800 px-2 py-2">
                        <p className="text-slate-300">
                          <span className="font-semibold">{category}</span>
                          <span className="ml-2 text-slate-500">({extensions.length})</span>
                        </p>
                        <p className="mt-1 font-mono text-[11px] text-slate-400">
                          {extensions.join(", ") || "-"}
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">Extractor Mapping</h4>
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                    {Object.entries(supportedTypes.extractor_doc_types).map(([docType, count]) => (
                      <div key={docType} className="rounded-md border border-slate-800 px-2 py-1">
                        <span className="font-mono">{docType}</span>: {count}
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">OCR-Capable Extensions</h4>
                  <p className="font-mono text-[11px] text-slate-400">
                    {supportedTypes.ocr_capable_extensions.join(", ") || "-"}
                  </p>
                </Card>
              </div>
            )}
          </aside>
        </div>
      )}

      {provenanceOpen && (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setProvenanceOpen(false)}
            aria-label="Close provenance panel"
          />

          <aside
            className="absolute right-0 top-0 h-full w-full max-w-[560px] overflow-y-auto border-l border-slate-700 bg-slate-950 p-5 shadow-2xl"
            data-testid="storage-provenance-panel"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Provenance Inspect</h3>
                <p className="text-xs text-slate-400">Raw source to node/event lineage</p>
              </div>
              <Button
                size="icon-sm"
                variant="ghost"
                onClick={() => setProvenanceOpen(false)}
                aria-label="Close"
              >
                <X size={14} />
              </Button>
            </div>

            {provenanceLoading ? (
              <div className="rounded-lg border border-slate-800 px-4 py-8 text-center text-sm text-slate-400">
                Loading provenance...
              </div>
            ) : !provenanceData ? (
              <div className="rounded-lg border border-slate-800 px-4 py-8 text-center text-sm text-slate-500">
                No provenance loaded for {shortId(provenanceRawId)}.
              </div>
            ) : (
              <div className="space-y-4">
                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">File</h4>
                  <div className="text-xs text-slate-300">
                    <p><span className="text-slate-500">filename:</span> {provenanceData.file.filename}</p>
                    <p><span className="text-slate-500">raw_id:</span> <span className="font-mono">{provenanceData.file.raw_id}</span></p>
                    <p><span className="text-slate-500">sha256:</span> <span className="font-mono">{provenanceData.file.sha256}</span></p>
                    <p><span className="text-slate-500">status:</span> {provenanceData.file.ingest_status}</p>
                    <p><span className="text-slate-500">size:</span> {formatBytes(provenanceData.file.size_bytes)}</p>
                  </div>
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">Raw Ref</h4>
                  {provenanceData.raw_ref ? (
                    <div className="text-xs text-slate-300">
                      <p><span className="text-slate-500">mime:</span> {provenanceData.raw_ref.mime_type}</p>
                      <p><span className="text-slate-500">uri:</span> <span className="font-mono">{redactUri(provenanceData.raw_ref.uri)}</span></p>
                      <p><span className="text-slate-500">created:</span> {provenanceData.raw_ref.created_at ? new Date(provenanceData.raw_ref.created_at).toLocaleString() : "-"}</p>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No raw_ref record available.</p>
                  )}
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300">Dedup</h4>
                  <div className="text-xs text-slate-300">
                    <p><span className="text-slate-500">packet_hash:</span> <span className="font-mono">{provenanceData.dedup.packet_hash || "-"}</span></p>
                    <p><span className="text-slate-500">dedup_record_found:</span> {String(provenanceData.dedup.dedup_record_found)}</p>
                    <p><span className="text-slate-500">dedup_raw_id:</span> <span className="font-mono">{provenanceData.dedup.dedup_raw_id || "-"}</span></p>
                    <p><span className="text-slate-500">dedup_node_count:</span> {provenanceData.dedup.dedup_node_count}</p>
                  </div>
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-slate-300">Nodes</h4>
                    <span className="text-[11px] text-slate-500">{provenanceData.node_count} total</span>
                  </div>
                  {provenanceData.nodes.length === 0 ? (
                    <p className="text-xs text-slate-500">No linked nodes.</p>
                  ) : (
                    <div className="max-h-44 space-y-1 overflow-auto text-[11px] text-slate-300">
                      {provenanceData.nodes.map((node) => (
                        <div key={node.node_id} className="rounded-md border border-slate-800 px-2 py-1">
                          <p className="font-mono">{shortId(node.node_id)} | {node.kind}</p>
                          <p className="text-slate-500">vector: {shortId(node.vector_hash)} | block: {node.block_id || "-"}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                <Card className="os-card rounded-2xl space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-slate-300">Events</h4>
                    <span className="text-[11px] text-slate-500">{provenanceData.event_count} shown</span>
                  </div>
                  {provenanceData.events.length === 0 ? (
                    <p className="text-xs text-slate-500">No matching provenance events.</p>
                  ) : (
                    <div className="max-h-52 space-y-1 overflow-auto text-[11px] text-slate-300">
                      {provenanceData.events.map((event) => (
                        <div key={`${event.seq}-${event.kind}`} className="rounded-md border border-slate-800 px-2 py-1">
                          <div className="flex items-center justify-between gap-2">
                            <span>#{event.seq} {event.kind}</span>
                            <span className="text-slate-500">
                              {event.ts ? new Date(event.ts).toLocaleString() : "-"}
                            </span>
                          </div>
                          <p className="mt-0.5 text-slate-500">keys: {event.payload_keys.join(", ") || "-"}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
