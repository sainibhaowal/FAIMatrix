"use client";

import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileText,
  HardDrive,
  RefreshCw,
  RotateCcw,
  Search,
  Shield,
  UploadCloud,
  XCircle,
} from "lucide-react";
import { getSession, useSession } from "next-auth/react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge, Button, Card, Input, Progress, useToast } from "@/components/ui";

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
  files: UploadResult[];
};

type FileListResponse = {
  items: StorageFileItem[];
  total: number;
  limit: number;
  offset: number;
};

const PAGE_SIZE = 20;

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, exp);
  return `${value.toFixed(value >= 100 || exp === 0 ? 0 : 1)} ${units[exp]}`;
}

function statusVariant(status: string): "default" | "success" | "warning" | "error" | "info" {
  if (status === "ingested" || status === "dedup_hit") return "success";
  if (status === "failed") return "error";
  if (status === "ingesting") return "info";
  if (status === "delete_requested") return "warning";
  return "default";
}

async function authHeaders(): Promise<HeadersInit> {
  const session = await getSession();
  const headers: Record<string, string> = {};
  const token = (session as any)?.accessToken;
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export default function StoragePage() {
  const { data: session } = useSession();
  const { toast } = useToast();

  const graphId = (session as any)?.graphId || "default";

  const [files, setFiles] = useState<StorageFileItem[]>([]);
  const [summary, setSummary] = useState<StorageSummary | null>(null);
  const [backends, setBackends] = useState<StorageBackends | null>(null);
  const [total, setTotal] = useState(0);

  const [loadingFiles, setLoadingFiles] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [actionRawId, setActionRawId] = useState<string | null>(null);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [batchResult, setBatchResult] = useState<UploadBatchResponse | null>(null);

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [profile, setProfile] = useState("strict");
  const [persistMode, setPersistMode] = useState("relaxed");

  const totalPages = useMemo(() => {
    if (!total) return 1;
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }, [total]);

  const fetchFiles = useCallback(async () => {
    setLoadingFiles(true);
    try {
      const headers = await authHeaders();
      const params = new URLSearchParams({
        graph_id: graphId,
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });
      if (statusFilter) params.set("status", statusFilter);
      if (query.trim()) params.set("q", query.trim());

      const res = await fetch(`/api/v1/storage/files?${params.toString()}`, {
        headers,
        cache: "no-store",
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Failed to load files");
      }
      const data: FileListResponse = await res.json();
      setFiles(data.items || []);
      setTotal(data.total || 0);
    } catch (e: any) {
      toast.error("Failed to load storage files", e?.message || "Unknown error");
    } finally {
      setLoadingFiles(false);
    }
  }, [graphId, page, query, statusFilter, toast]);

  const fetchSummary = useCallback(async () => {
    setLoadingSummary(true);
    try {
      const headers = await authHeaders();

      const [summaryRes, backendsRes] = await Promise.all([
        fetch(`/api/v1/storage/summary?graph_id=${encodeURIComponent(graphId)}`, {
          headers,
          cache: "no-store",
        }),
        fetch(`/api/v1/storage/backends/health`, {
          headers,
          cache: "no-store",
        }),
      ]);

      if (summaryRes.ok) {
        const summaryData: StorageSummary = await summaryRes.json();
        setSummary(summaryData);
      }
      if (backendsRes.ok) {
        const backendData: StorageBackends = await backendsRes.json();
        setBackends(backendData);
      }
    } catch (e: any) {
      toast.warning("Storage summary unavailable", e?.message || "Try refresh");
    } finally {
      setLoadingSummary(false);
    }
  }, [graphId, toast]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  useEffect(() => {
    const id = setInterval(() => {
      fetchSummary();
    }, 15000);
    return () => clearInterval(id);
  }, [fetchSummary]);

  const handleSelectFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const incoming = Array.from(event.target.files || []);
    setSelectedFiles(incoming);
  };

  const uploadProgress = useMemo(() => {
    if (!selectedFiles.length || !batchResult) return 0;
    return Math.round((batchResult.processed_files / Math.max(1, batchResult.requested_files)) * 100);
  }, [batchResult, selectedFiles.length]);

  const handleUpload = async () => {
    if (!selectedFiles.length) {
      toast.warning("No files selected", "Pick one or more files to upload");
      return;
    }

    setUploading(true);
    setBatchResult(null);

    try {
      const headers = await authHeaders();
      const formData = new FormData();
      formData.set("graph_id", graphId);
      formData.set("profile", profile);
      formData.set("persist_mode", persistMode);
      for (const file of selectedFiles) {
        formData.append("files", file);
      }

      const res = await fetch(`/api/v1/storage/uploads`, {
        method: "POST",
        headers,
        body: formData,
      });

      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(payload?.detail || "Upload failed");
      }

      const batch: UploadBatchResponse = payload;
      setBatchResult(batch);
      setSelectedFiles([]);

      if (batch.failed_files > 0) {
        toast.warning(
          "Upload completed with failures",
          `${batch.success_files} succeeded, ${batch.failed_files} failed`
        );
      } else {
        toast.success(
          "Upload completed",
          `${batch.success_files} files ingested (${batch.dedup_hits} dedup hits)`
        );
      }

      setPage(0);
      await Promise.all([fetchFiles(), fetchSummary()]);
    } catch (e: any) {
      toast.error("Upload failed", e?.message || "Unknown error");
    } finally {
      setUploading(false);
    }
  };

  const runFileAction = async (
    rawId: string,
    action: "ingest" | "retry" | "delete"
  ) => {
    setActionRawId(rawId);
    try {
      const headers = await authHeaders();
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

      const res = await fetch(url, {
        method,
        headers,
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(payload?.detail || `${action} failed`);
      }

      if (action === "delete") {
        toast.info("Delete request submitted", "File marked as delete_requested");
      } else if (action === "retry") {
        toast.success("Retry finished", payload?.ingest?.status || "done");
      } else {
        toast.success("Re-ingest finished", payload?.ingest?.status || "done");
      }

      await Promise.all([fetchFiles(), fetchSummary()]);
    } catch (e: any) {
      toast.error(`Failed to ${action}`, e?.message || "Unknown error");
    } finally {
      setActionRawId(null);
    }
  };

  const ingestedCount = summary?.by_status?.ingested || 0;
  const failedCount = summary?.by_status?.failed || 0;
  const dedupCount = summary?.by_status?.dedup_hit || 0;

  return (
    <div className="space-y-6 pb-8 text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Storage Control Plane</h1>
          <p className="mt-1 text-sm text-slate-400">
            Multi-file upload, ingest lifecycle tracking, and immutable raw provenance for graph `{graphId}`.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          leftIcon={<RefreshCw size={14} />}
          onClick={async () => {
            await Promise.all([fetchFiles(), fetchSummary()]);
          }}
        >
          Refresh
        </Button>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card className="os-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Total Files</p>
              <p className="mt-1 text-2xl font-semibold">{summary?.total_files ?? 0}</p>
            </div>
            <FileText className="text-cyan-400" size={20} />
          </div>
        </Card>
        <Card className="os-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Stored Bytes</p>
              <p className="mt-1 text-2xl font-semibold">{formatBytes(summary?.total_bytes ?? 0)}</p>
            </div>
            <HardDrive className="text-violet-400" size={20} />
          </div>
        </Card>
        <Card className="os-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400">Ingested</p>
              <p className="mt-1 text-2xl font-semibold">{ingestedCount}</p>
              <p className="text-xs text-slate-500">Dedup hits: {dedupCount}</p>
            </div>
            <CheckCircle2 className="text-emerald-400" size={20} />
          </div>
        </Card>
        <Card className="os-card">
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

      <Card className="os-card space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Batch Upload</h2>
            <p className="text-xs text-slate-400">Uploads are persisted as immutable raw blobs before ingest.</p>
          </div>
          <div className="flex items-center gap-2">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs hover:bg-slate-900/40">
              <UploadCloud size={14} />
              Select Files
              <input type="file" multiple className="hidden" onChange={handleSelectFiles} />
            </label>
            <Button
              size="sm"
              loading={uploading}
              onClick={handleUpload}
              disabled={!selectedFiles.length || uploading}
            >
              Upload & Ingest
            </Button>
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
            <label className="mb-1 block text-xs text-slate-400">Selected</label>
            <div className="h-9 rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm leading-9 text-slate-300">
              {selectedFiles.length} file(s)
            </div>
          </div>
        </div>

        {!!selectedFiles.length && (
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <p className="mb-2 text-xs text-slate-400">Pending Files</p>
            <div className="max-h-32 space-y-1 overflow-auto pr-1 text-xs text-slate-300">
              {selectedFiles.map((f) => (
                <div key={`${f.name}-${f.size}`} className="flex items-center justify-between">
                  <span className="truncate">{f.name}</span>
                  <span className="text-slate-500">{formatBytes(f.size)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {batchResult && (
          <div className="space-y-2 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-300">
              <span>Batch `{batchResult.job_id}`</span>
              <span>
                {batchResult.success_files} success / {batchResult.failed_files} failed / {batchResult.dedup_hits} dedup
              </span>
            </div>
            <Progress value={uploadProgress} showLabel label="Batch Progress" variant="gradient" />
            <div className="max-h-40 space-y-1 overflow-auto pr-1">
              {batchResult.files.map((f) => (
                <div
                  key={`${f.filename}-${f.raw_id || "na"}`}
                  className="flex items-center justify-between rounded-md border border-slate-800 px-2 py-1 text-xs"
                >
                  <span className="truncate pr-2">{f.filename}</span>
                  <Badge size="xs" variant={statusVariant(f.status)}>
                    {f.status}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      <Card className="os-card space-y-4">
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
            onChange={(e) => {
              setPage(0);
              setQuery(e.target.value);
            }}
            placeholder="Search filename or hash"
            leftIcon={<Search size={14} />}
          />
          <select
            value={statusFilter}
            onChange={(e) => {
              setPage(0);
              setStatusFilter(e.target.value);
            }}
            className="h-9 rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm"
          >
            <option value="">All statuses</option>
            <option value="uploaded">uploaded</option>
            <option value="ingesting">ingesting</option>
            <option value="ingested">ingested</option>
            <option value="dedup_hit">dedup_hit</option>
            <option value="failed">failed</option>
            <option value="delete_requested">delete_requested</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={() => {
              fetchFiles();
              fetchSummary();
            }}
          >
            Refresh Catalog
          </Button>
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full min-w-[980px] text-left text-xs">
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
                        <div className="max-w-[260px] truncate text-slate-200">{row.filename}</div>
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
                      <td className="px-3 py-2 font-mono text-[11px] text-slate-400">{row.raw_id.slice(0, 12)}...</td>
                      <td className="px-3 py-2 text-slate-400">
                        {row.updated_at ? new Date(row.updated_at).toLocaleString() : "-"}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-1">
                          <Button
                            size="xs"
                            variant="outline"
                            className="h-7"
                            disabled={busy || row.delete_requested}
                            onClick={() => runFileAction(row.raw_id, "ingest")}
                          >
                            Re-ingest
                          </Button>
                          <Button
                            size="xs"
                            variant="outline"
                            className="h-7"
                            disabled={busy || row.ingest_status !== "failed"}
                            leftIcon={<RotateCcw size={12} />}
                            onClick={() => runFileAction(row.raw_id, "retry")}
                          >
                            Retry
                          </Button>
                          <Button
                            size="xs"
                            variant="danger"
                            className="h-7"
                            disabled={busy || row.delete_requested}
                            onClick={() => runFileAction(row.raw_id, "delete")}
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
          <span>
            {loadingSummary ? "Loading summary..." : `Total ${total} file(s)`}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="xs"
              className="h-7"
              disabled={page <= 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
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
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
