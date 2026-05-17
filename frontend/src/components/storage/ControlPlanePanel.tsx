"use client";

import { Activity } from "lucide-react";
import { getSession, useSession } from "next-auth/react";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import { Badge, Button, Input, useToast } from "@/components/ui";

type StorageMaintenanceHistoryItem = {
  seq: number;
  kind: string;
  ts?: string | null;
  status: string;
  summary: string;
  graph_version?: number | null;
  payload: Record<string, unknown>;
};

type StorageMaintenanceHistoryResponse = {
  graph_id: string;
  total: number;
  items: StorageMaintenanceHistoryItem[];
};

type MaintenanceActionKey =
  | "canonical"
  | "multilingual"
  | "multimodal"
  | "domain_profile"
  | "domain_knowledge"
  | "repr_v2"
  | "prune_cold_dry"
  | "prune_cold_live"
  | "cluster";

function formatWhen(value?: string | null): string {
  if (!value) return "—";
  const ts = Date.parse(value);
  if (Number.isNaN(ts)) return value;
  return new Date(ts).toLocaleString();
}

function maintenanceActionSummary(
  action: MaintenanceActionKey,
  response: Record<string, unknown>,
): string {
  const n = (value: unknown): number => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  if (action === "canonical") {
    return `Canonical rebuild: files ${n(response.files_scanned)}, terms ${n(response.term_stats_written)}, edges ${n(response.edges_written)}`;
  }
  if (action === "multilingual") {
    return `Multilingual rebuild: files ${n(response.files_scanned)}, concepts ${n(response.concept_nodes_written)}, edges ${n(response.concept_edges_written)}`;
  }
  if (action === "multimodal") {
    return `Multimodal backfill: files ${n(response.files_scanned)}, inserted ${n(response.inserted)}, updated ${n(response.updated)}`;
  }
  if (action === "domain_profile") {
    return `Domain profile: files ${n(response.files_scanned)}, terms ${n(response.lexicon_written)}`;
  }
  if (action === "repr_v2") {
    return `Memory index rebuild: scanned ${n(response.files_scanned)} files, matched ${n(response.matched_nodes)} nodes, updated ${n(response.updated)}, inserted ${n(response.inserted)}, skipped ${n(response.skipped_nodes)}`;
  }
  if (action === "prune_cold_dry") {
    return `Prune preview (dry run): ${n(response.scanned)} cold candidates found — run live prune to delete them`;
  }
  if (action === "prune_cold_live") {
    return `Pruned ${n(response.pruned)} cold nodes (age >${n(response.cold_age_days)}d, never accessed)`;
  }
  if (action === "cluster") {
    return `Clustering complete: k=${n(response.k)}, ${n(response.nodes_clustered)} nodes assigned, ${n(response.iterations)} iterations${response.converged ? " (converged)" : ""}`;
  }
  return `Domain knowledge import: entities ${n(response.entity_nodes_written)}, facts ${n(response.fact_nodes_written)}, edges ${n(response.edges_written)}`;
}

function _normalizeHeaders(init?: HeadersInit): Record<string, string> {
  if (!init) return {};
  if (init instanceof Headers) return Object.fromEntries(init.entries());
  if (Array.isArray(init)) return Object.fromEntries(init);
  return { ...(init as Record<string, string>) };
}

async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const base: Record<string, string> = {};
  if (token) base.Authorization = `Bearer ${token}`;
  return { ...base, ..._normalizeHeaders(extra) };
}

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

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
    const message =
      (payload as { detail?: unknown; error?: unknown } | null)?.detail ||
      (payload as { message?: unknown } | null)?.message ||
      (payload as { error?: unknown } | null)?.error ||
      response.statusText ||
      `HTTP ${response.status}`;
    throw new ApiError(response.status, String(message));
  }

  return (payload as T) || ({} as T);
}

export function ControlPlanePanel() {
  const { data: session, status: sessionStatus } = useSession();
  const { toast } = useToast();
  const sessionGraphId = useMemo(() => {
    return String(
      (session as { graphId?: string } | null)?.graphId || "default",
    ).trim();
  }, [session]);
  const accessToken = (session as { accessToken?: string } | null)?.accessToken;
  const isAuthenticated =
    sessionStatus === "authenticated" && Boolean(accessToken);

  const [graphScopeInput, setGraphScopeInput] = useState(sessionGraphId);
  const [graphScope, setGraphScope] = useState(sessionGraphId);
  const [maintenanceHistory, setMaintenanceHistory] = useState<
    StorageMaintenanceHistoryItem[]
  >([]);
  const [loadingMaintenanceHistory, setLoadingMaintenanceHistory] =
    useState(false);
  const [maintenanceBusy, setMaintenanceBusy] =
    useState<MaintenanceActionKey | null>(null);
  const [domainKnowledgeText, setDomainKnowledgeText] = useState(
    JSON.stringify(
      [
        {
          entity: "Acme Corp",
          relation: "headquartered_in",
          value: "Berlin",
          time: "",
          aliases: ["Acme"],
          source_id: "acme-corp-hq",
          source_kind: "manual",
          meta: { confidence: 0.9 },
        },
      ],
      null,
      2,
    ),
  );

  const activeGraphId = useMemo(
    () => graphScope.trim() || sessionGraphId,
    [graphScope, sessionGraphId],
  );

  useEffect(() => {
    setGraphScopeInput(sessionGraphId);
    setGraphScope(sessionGraphId);
  }, [sessionGraphId]);

  const fetchMaintenanceHistoryInternal = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoadingMaintenanceHistory(true);
    try {
      const data = await fetchJson<StorageMaintenanceHistoryResponse>(
        `/api/v1/storage/maintenance/history?graph_id=${encodeURIComponent(activeGraphId)}&limit=10`,
      );
      setMaintenanceHistory(data.items || []);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      if (error instanceof ApiError && error.status === 429) {
        toast.warning("Maintenance history rate-limited", message);
      } else {
        toast.warning("Maintenance history unavailable", message);
      }
    } finally {
      setLoadingMaintenanceHistory(false);
    }
  }, [activeGraphId, isAuthenticated, toast]);

  useEffect(() => {
    if (isAuthenticated) {
      void fetchMaintenanceHistoryInternal();
    }
  }, [fetchMaintenanceHistoryInternal, isAuthenticated]);

  const applyGraphScope = useCallback(() => {
    const next = graphScopeInput.trim() || sessionGraphId;
    if (next === graphScope) return;
    setGraphScope(next);
    setMaintenanceHistory([]);
    toast.info("Graph scope updated", `Control plane now targets ${next}`);
  }, [graphScope, graphScopeInput, sessionGraphId, toast]);

  const runMaintenanceAction = useCallback(
    async (action: MaintenanceActionKey) => {
      if (maintenanceBusy || !isAuthenticated) return;
      setMaintenanceBusy(action);
      try {
        let response: Record<string, unknown> = {};

        if (action === "canonical") {
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/canonical-semantics/rebuild`,
            { method: "POST" },
          );
        } else if (action === "multilingual") {
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/multilingual-semantics/rebuild`,
            { method: "POST" },
          );
        } else if (action === "multimodal") {
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/multimodal/rebuild`,
            { method: "POST" },
          );
        } else if (action === "domain_profile") {
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/domain-profile/rebuild`,
            { method: "POST" },
          );
        } else if (action === "repr_v2") {
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/representation-v2/rebuild`,
            { method: "POST" },
          );
        } else if (action === "prune_cold_dry") {
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/prune-cold-nodes?dry_run=true&cold_age_days=90`,
            { method: "POST" },
          );
        } else if (action === "prune_cold_live") {
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/prune-cold-nodes?dry_run=false&cold_age_days=90`,
            { method: "POST" },
          );
        } else if (action === "cluster") {
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/cluster`,
            { method: "POST" },
          );
        } else if (action === "domain_knowledge") {
          let kbRows: unknown;
          try {
            kbRows = JSON.parse(domainKnowledgeText);
          } catch {
            throw new Error("Domain knowledge input must be valid JSON.");
          }
          if (!Array.isArray(kbRows)) {
            throw new Error(
              "Domain knowledge input must be a JSON array of rows.",
            );
          }
          response = await fetchJson<Record<string, unknown>>(
            `/api/v1/storage/graphs/${encodeURIComponent(activeGraphId)}/domain-knowledge/import`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                kb_rows: kbRows,
              }),
            },
          );
        }

        toast.success(
          "Maintenance completed",
          maintenanceActionSummary(action, response),
        );
        await fetchMaintenanceHistoryInternal();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Unknown error";
        toast.error("Maintenance failed", message);
      } finally {
        setMaintenanceBusy(null);
      }
    },
    [
      activeGraphId,
      domainKnowledgeText,
      fetchMaintenanceHistoryInternal,
      isAuthenticated,
      maintenanceBusy,
      toast,
    ],
  );

  return (
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
          Retrieval Control Plane
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Badge size="xs" variant="success">
            FAIM Native Extractor
          </Badge>
          <Badge size="xs" variant="info">
            Multi-column · Tables · Scanned PDFs · OCR
          </Badge>
        </div>
      </div>

      {!isAuthenticated && (
        <div className="mx-5 mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Control plane actions require an active signed-in session.
        </div>
      )}

      <div className="grid gap-4 px-5 py-4 xl:grid-cols-[1.15fr_.85fr]">
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
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
                  setMaintenanceHistory([]);
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

          {maintenanceBusy && (
            <div
              className="flex items-center gap-2 rounded-lg border px-3 py-2 text-xs"
              style={{
                borderColor: "rgba(99,102,241,0.25)",
                background: "rgba(99,102,241,0.08)",
                color: "var(--text-secondary)",
              }}
            >
              <Activity size={14} className="animate-spin" />
              Running {maintenanceBusy.replace("_", " ")} on {activeGraphId} ...
            </div>
          )}

          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {[
              { key: "cluster" as const, label: "Run Topic Clustering" },
              { key: "repr_v2" as const, label: "Rebuild Memory Index" },
              {
                key: "prune_cold_dry" as const,
                label: "Preview Cold Prune (dry run)",
              },
              {
                key: "prune_cold_live" as const,
                label: "Prune Cold Nodes (live)",
              },
              {
                key: "canonical" as const,
                label: "Canonical semantics rebuild",
              },
              {
                key: "multilingual" as const,
                label: "Multilingual semantics rebuild",
              },
              {
                key: "multimodal" as const,
                label: "Multimodal backfill/rebuild",
              },
              {
                key: "domain_profile" as const,
                label: "Domain profile rebuild",
              },
              {
                key: "domain_knowledge" as const,
                label: "Domain knowledge import",
              },
            ].map((action) => (
              <Button
                key={action.key}
                size="sm"
                variant="outline"
                className="justify-start"
                disabled={!!maintenanceBusy || !isAuthenticated}
                onClick={() => {
                  void runMaintenanceAction(action.key);
                }}
              >
                {maintenanceBusy === action.key ? (
                  <span className="inline-flex items-center gap-2">
                    <Activity size={12} className="animate-spin" />
                    Running...
                  </span>
                ) : (
                  action.label
                )}
              </Button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <div
            className="rounded-xl border px-3 py-3 text-xs"
            style={{
              borderColor: "var(--os-stroke)",
              background: "var(--os-surface-2)",
              color: "var(--text-tertiary)",
            }}
          >
            Auto mode is enforced here. Domain packs are disabled.
          </div>

          <div>
            <p
              className="mb-1.5 text-[10px] font-medium uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Domain Knowledge JSON
            </p>
            <textarea
              value={domainKnowledgeText}
              onChange={(e) => setDomainKnowledgeText(e.target.value)}
              className="min-h-[170px] w-full rounded-xl border px-3 py-2 text-xs outline-none transition-colors"
              style={{
                borderColor: "var(--os-stroke)",
                background: "var(--os-surface-2)",
                color: "var(--text-primary)",
              }}
            />
            <p
              className="mt-1 text-[11px]"
              style={{ color: "var(--text-tertiary)" }}
            >
              Paste a JSON array of{" "}
              <code className="font-mono text-[11px] text-slate-300">
                {
                  "{ entity, relation, value, time, aliases?, source_id?, source_kind?, meta? }"
                }
              </code>{" "}
              rows.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={!!maintenanceBusy || !isAuthenticated}
              onClick={() => {
                setDomainKnowledgeText(
                  JSON.stringify(
                    [
                      {
                        entity: "Acme Corp",
                        relation: "headquartered_in",
                        value: "Berlin",
                        time: "",
                        aliases: ["Acme"],
                        source_id: "acme-corp-hq",
                        source_kind: "manual",
                        meta: { confidence: 0.9 },
                      },
                    ],
                    null,
                    2,
                  ),
                );
              }}
            >
              Load sample
            </Button>
            <Button
              size="sm"
              variant="primary"
              disabled={!!maintenanceBusy || !isAuthenticated}
              onClick={() => {
                void runMaintenanceAction("domain_knowledge");
              }}
            >
              Import KB rows
            </Button>
          </div>
        </div>
      </div>

      <div
        className="border-t px-5 py-4"
        style={{ borderColor: "var(--os-stroke)" }}
      >
        <div className="flex items-center justify-between gap-3">
          <p
            className="text-[10px] font-medium uppercase tracking-widest"
            style={{ color: "var(--text-tertiary)" }}
          >
            Maintenance History
          </p>
          <span
            className="text-[11px]"
            style={{ color: "var(--text-tertiary)" }}
          >
            {loadingMaintenanceHistory
              ? "Refreshing..."
              : `${maintenanceHistory.length} recent run(s)`}
          </span>
        </div>
        <div className="mt-3 grid gap-3 xl:grid-cols-2">
          {maintenanceHistory.length === 0 ? (
            <div
              className="rounded-lg border px-3 py-3 text-xs"
              style={{
                borderColor: "var(--os-stroke)",
                background: "var(--os-surface-2)",
                color: "var(--text-tertiary)",
              }}
            >
              No maintenance runs recorded for this graph yet.
            </div>
          ) : (
            maintenanceHistory.map((item) => (
              <div
                key={`${item.kind}-${item.seq}`}
                className="rounded-lg border px-3 py-3 text-xs"
                style={{
                  borderColor: "var(--os-stroke)",
                  background: "var(--os-surface-2)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <p
                    className="font-medium"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {item.kind.replaceAll("_", " ").toLowerCase()}
                  </p>
                  <Badge
                    size="xs"
                    variant={
                      item.status === "completed"
                        ? "success"
                        : item.status === "failed"
                          ? "error"
                          : "default"
                    }
                  >
                    {item.status}
                  </Badge>
                </div>
                <p
                  className="mt-1 text-[11px]"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {item.summary}
                </p>
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
                  <span>seq {item.seq}</span>
                  <span>{formatWhen(item.ts)}</span>
                  {item.graph_version ? (
                    <span>gv {item.graph_version}</span>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
