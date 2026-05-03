"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import {
  Activity,
  Bell,
  Database,
  Mail,
  RefreshCw,
  ServerCog,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { readJsonSafely } from "@/lib/safeFetch";

type BackupItem = {
  name: string;
  kind: string;
  compressed: boolean;
  path: string;
  size_bytes: number;
  modified_at: string;
};

type AdminAlert = {
  id: string;
  severity: "critical" | "warning" | "info" | "success" | string;
  title: string;
  message: string;
  source: string;
  created_at: string;
  acknowledged?: boolean;
};

type AlertDelivery = {
  provider?: string;
  enabled?: boolean;
  from_email?: string;
  recipients?: string[];
  recipients_count?: number;
};

type AdminStatus = {
  status: string;
  health: {
    status?: string;
    timestamp?: string;
  };
  readiness: {
    status?: string;
    db_connected?: boolean;
    tables_ok?: boolean;
    migrations_ok?: boolean;
    latest_migration?: number;
    applied_migration?: number;
    missing_tables?: string[];
  };
  version: {
    version?: string;
    stage?: string;
    build_time?: string;
    features?: Record<string, boolean>;
  };
  runtime: {
    env?: string;
    mode?: string;
    public_origin?: string;
    cors_origins?: string[];
    backup_dir?: string;
    raw_store_path?: string;
    auth_db_primary?: boolean;
    auth_scope_enforcement_enabled?: boolean;
    enable_cache?: boolean;
    enable_index?: boolean;
    enable_jobs?: boolean;
    admin_key_configured?: boolean;
  };
  backups: BackupItem[];
  alerts: AdminAlert[];
  alert_delivery: AlertDelivery;
};

type ActionResult = {
  status: string;
  message: string;
  details?: Record<string, unknown>;
};

type AdminView = "overview" | "alerts";

function prettySize(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${units[idx]}`;
}

function formatWhen(value?: string): string {
  if (!value) return "—";
  const ts = Date.parse(value);
  if (Number.isNaN(ts)) return value;
  return new Date(ts).toLocaleString();
}

export function AdminControlPlane({ view }: { view: AdminView }) {
  const { data: session, status: sessionStatus } = useSession();
  const [adminStatus, setAdminStatus] = useState<AdminStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [graphId, setGraphId] = useState<string>("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<ActionResult | null>(null);
  const [alertActionLoading, setAlertActionLoading] = useState<string | null>(
    null,
  );
  const [alertActionResult, setAlertActionResult] =
    useState<ActionResult | null>(null);
  const isAdmin = Boolean((session as { isAdmin?: boolean } | null)?.isAdmin);

  const sessionGraphId = useMemo(() => {
    return String((session as { graphId?: string } | null)?.graphId || "").trim();
  }, [session]);

  useEffect(() => {
    if (sessionGraphId && !graphId) {
      setGraphId(sessionGraphId);
    }
  }, [graphId, sessionGraphId]);

  const loadStatus = async () => {
    setLoadingStatus(true);
    setStatusError(null);
    try {
      const res = await fetch("/api/admin/status", { cache: "no-store" });
      const data = await readJsonSafely<AdminStatus>(res);
      if (!res.ok || !data) {
        throw new Error(
          `Status request failed (${res.status})${data ? "" : ": non-JSON response"}`,
        );
      }
      setAdminStatus(data);
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : "Status unavailable");
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    if (sessionStatus === "authenticated" && isAdmin) {
      void loadStatus();
    } else if (sessionStatus !== "loading") {
      setLoadingStatus(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionStatus, isAdmin]);

  const runAction = async (
    path: "reindex" | "snapshot/create" | "replay/verify",
  ) => {
    if (!graphId.trim()) {
      setActionResult({
        status: "error",
        message: "Enter a graph ID first.",
      });
      return;
    }
    setActionLoading(path);
    setActionResult(null);
    try {
      const res = await fetch(`/api/admin/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ graph_id: graphId.trim() }),
      });
      const data = await readJsonSafely<ActionResult>(res);
      if (!res.ok || !data) {
        throw new Error(
          `Action failed (${res.status})${data ? "" : ": non-JSON response"}`,
        );
      }
      setActionResult(data);
      await loadStatus();
    } catch (err) {
      setActionResult({
        status: "error",
        message: err instanceof Error ? err.message : "Action failed",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const runAlertAction = async (path: "alerts/send" | "alerts/test") => {
    setAlertActionLoading(path);
    setAlertActionResult(null);
    try {
      const res = await fetch(`/api/admin/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await readJsonSafely<ActionResult>(res);
      if (!res.ok || !data) {
        throw new Error(
          `Alert action failed (${res.status})${data ? "" : ": non-JSON response"}`,
        );
      }
      setAlertActionResult(data);
      await loadStatus();
    } catch (err) {
      setAlertActionResult({
        status: "error",
        message: err instanceof Error ? err.message : "Alert action failed",
      });
    } finally {
      setAlertActionLoading(null);
    }
  };

  const latestBackup = adminStatus?.backups?.[0];
  const alerts = adminStatus?.alerts ?? [];
  const alertDelivery = adminStatus?.alert_delivery;
  const criticalAlerts = alerts.filter((item) => item.severity === "critical");
  const warningAlerts = alerts.filter((item) => item.severity === "warning");

  const headerActions = (
    <div className="flex items-center gap-2">
      <Link
        href={view === "alerts" ? "/dashboard/admin" : "/dashboard/admin/alerts"}
        className="inline-flex h-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] px-3 text-xs font-medium text-slate-200 transition-colors hover:border-cyan-500/30 hover:bg-cyan-500/10 hover:text-cyan-100"
      >
        {view === "alerts" ? "Back to Admin" : "Open Alerts"}
      </Link>
      <Button
        variant="outline"
        size="sm"
        onClick={() => void loadStatus()}
        leftIcon={<RefreshCw className="h-4 w-4" />}
      >
        Refresh
      </Button>
    </div>
  );

  if (sessionStatus === "loading" || loadingStatus) {
    return (
      <div className="space-y-6">
        <GlassHeader
          title="Admin"
          subtitle="Restricted control plane"
          icon={Shield}
          actions={headerActions}
        />
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 text-sm text-slate-400">
          Loading admin control plane...
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <GlassHeader
          title="Admin"
          subtitle="Restricted control plane"
          icon={Shield}
          actions={headerActions}
        />
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 text-sm text-rose-200">
          Admin access is not enabled for this account.
        </div>
      </div>
    );
  }

  const isAlertsView = view === "alerts";

  return (
    <div className="space-y-6">
      <GlassHeader
        title={isAlertsView ? "Alerts" : "Admin"}
        subtitle={
          isAlertsView
            ? "Operational alerts and email delivery"
            : "Restricted control plane for backups, runtime status, and graph repairs"
        }
        icon={isAlertsView ? Bell : ShieldCheck}
        actions={headerActions}
      />

      {statusError && (
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-100">
          {statusError}
        </div>
      )}

      {!isAlertsView ? (
        <>
          <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
            <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    System
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">
                    Runtime snapshot
                  </div>
                </div>
                <Badge
                  variant={adminStatus?.status === "ok" ? "success" : "warning"}
                  size="md"
                >
                  {adminStatus?.status || "unknown"}
                </Badge>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <StatusTile
                  label="Health"
                  value={adminStatus?.health?.status ?? "unknown"}
                  meta={adminStatus?.health?.timestamp}
                  tone={adminStatus?.health?.status === "ok" ? "success" : "warning"}
                />
                <StatusTile
                  label="Readiness"
                  value={adminStatus?.readiness?.status ?? "unknown"}
                  meta={`DB: ${adminStatus?.readiness?.db_connected ? "ok" : "down"} · Tables: ${adminStatus?.readiness?.tables_ok ? "ok" : "missing"} · Migrations: ${adminStatus?.readiness?.migrations_ok ? "ok" : "pending"}`}
                  tone={adminStatus?.readiness?.status === "ready" ? "success" : "warning"}
                />
                <StatusTile
                  label="Version"
                  value={adminStatus?.version?.version ?? "unknown"}
                  meta={`Stage ${adminStatus?.version?.stage ?? "—"} · Built ${formatWhen(adminStatus?.version?.build_time)}`}
                  tone="neutral"
                />
                <StatusTile
                  label="Admin auth"
                  value={
                    adminStatus?.runtime?.admin_key_configured ? "configured" : "missing"
                  }
                  meta={`Mode ${adminStatus?.runtime?.mode ?? "—"} · Auth ${adminStatus?.runtime?.auth_db_primary ? "db" : "fallback"}`}
                  tone={adminStatus?.runtime?.admin_key_configured ? "success" : "warning"}
                />
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <InfoRow
                  label="Public origin"
                  value={adminStatus?.runtime?.public_origin ?? "—"}
                />
                <InfoRow
                  label="Backup dir"
                  value={adminStatus?.runtime?.backup_dir ?? "—"}
                />
                <InfoRow
                  label="Raw store"
                  value={adminStatus?.runtime?.raw_store_path ?? "—"}
                />
                <InfoRow
                  label="CORS origins"
                  value={adminStatus?.runtime?.cors_origins?.join(", ") || "—"}
                />
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-cyan-200">
                  <Database className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Backups
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">
                    Recent inventory
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                {latestBackup ? (
                  <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-emerald-100">
                          {latestBackup.name}
                        </div>
                        <div className="mt-1 text-[11px] text-emerald-200/70">
                          {latestBackup.kind} · {prettySize(latestBackup.size_bytes)} ·{" "}
                          {formatWhen(latestBackup.modified_at)}
                        </div>
                      </div>
                      <Badge variant="success" size="sm">
                        newest
                      </Badge>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
                    No backups found in the configured directory.
                  </div>
                )}

                <div className="max-h-[280px] space-y-2 overflow-auto pr-1">
                  {(adminStatus?.backups ?? []).slice(0, 8).map((item) => (
                    <div
                      key={item.name}
                      className="rounded-2xl border border-white/10 bg-black/20 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium text-slate-100">
                            {item.name}
                          </div>
                          <div className="mt-1 text-[11px] text-slate-500">
                            {item.kind} · {item.compressed ? "compressed" : "plain"} ·{" "}
                            {prettySize(item.size_bytes)}
                          </div>
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {formatWhen(item.modified_at)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>

          <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl border border-violet-500/20 bg-violet-500/10 p-3 text-violet-200">
                  <ServerCog className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Graph repair
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">
                    Admin actions
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
                <label className="block">
                  <span className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Target graph
                  </span>
                  <input
                    value={graphId}
                    onChange={(e) => setGraphId(e.target.value)}
                    placeholder={sessionGraphId || "U:..."}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-500/50"
                  />
                </label>
                <div className="flex flex-wrap items-end gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => void runAction("reindex")}
                    loading={actionLoading === "reindex"}
                    leftIcon={<Activity className="h-4 w-4" />}
                  >
                    Reindex
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => void runAction("snapshot/create")}
                    loading={actionLoading === "snapshot/create"}
                    leftIcon={<Sparkles className="h-4 w-4" />}
                  >
                    Snapshot
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => void runAction("replay/verify")}
                    loading={actionLoading === "replay/verify"}
                    leftIcon={<Shield className="h-4 w-4" />}
                  >
                    Verify replay
                  </Button>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  <ShieldAlert className="h-4 w-4 text-amber-300" />
                  Safety
                </div>
                <p className="mt-2 leading-6 text-slate-400">
                  These actions run through the restricted admin bridge. The browser
                  only sees your signed-in admin session; the backend admin key
                  stays server-side.
                </p>
              </div>

              {actionResult && (
                <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-white">
                      Action result
                    </div>
                    <Badge
                      variant={actionResult.status === "error" ? "error" : "success"}
                      size="sm"
                    >
                      {actionResult.status}
                    </Badge>
                  </div>
                  <div className="mt-2 text-sm text-slate-300">
                    {actionResult.message}
                  </div>
                  {actionResult.details && (
                    <pre className="mt-3 overflow-auto rounded-xl border border-white/10 bg-black/40 p-3 text-[11px] text-slate-300">
                      {JSON.stringify(actionResult.details, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-3 text-amber-200">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Control details
                  </div>
                  <div className="mt-1 text-lg font-semibold text-white">
                    Validation summary
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                <InfoRow
                  label="Session"
                  value={(session?.user?.email as string) || "signed in"}
                />
                <InfoRow
                  label="Admin enabled"
                  value={String(Boolean((session as any)?.isAdmin))}
                />
                <InfoRow
                  label="Current graph"
                  value={sessionGraphId || graphId || "—"}
                />
                <InfoRow
                  label="Latest backup"
                  value={latestBackup?.name || "none"}
                />
              </div>

              <div className="mt-4 rounded-2xl border border-cyan-500/10 bg-cyan-500/5 p-4 text-sm text-cyan-50">
                Use this section only for operator actions. Consumer users should
                never see it.
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
                Alerts are separated onto their own page now.
                <div className="mt-3">
                  <Link
                    href="/dashboard/admin/alerts"
                    className="inline-flex items-center rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-100 transition-colors hover:bg-rose-500/20"
                  >
                    Open alerts page
                  </Link>
                </div>
              </div>
            </div>
          </section>
        </>
      ) : (
        <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-3 text-rose-200">
                <Bell className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Alerts
                </div>
                <div className="mt-1 text-lg font-semibold text-white">
                  Operational alerts
                </div>
              </div>
              <Badge variant={alerts.length ? "warning" : "success"} size="sm">
                {alerts.length ? `${alerts.length} active` : "clear"}
              </Badge>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <StatusTile
                label="Critical"
                value={String(criticalAlerts.length)}
                meta="Requires immediate operator action"
                tone={criticalAlerts.length ? "warning" : "success"}
              />
              <StatusTile
                label="Warnings"
                value={String(warningAlerts.length)}
                meta="Monitor and confirm recovery"
                tone={warningAlerts.length ? "warning" : "neutral"}
              />
              <StatusTile
                label="Delivery"
                value={alertDelivery?.provider ?? "resend"}
                meta={`To ${alertDelivery?.recipients_count ?? 0} recipient(s)`}
                tone={alertDelivery?.enabled ? "success" : "warning"}
              />
            </div>

            <div className="mt-4 space-y-2">
              {alerts.length ? (
                alerts.map((item) => (
                  <div
                    key={item.id}
                    className={`rounded-2xl border p-4 ${
                      item.severity === "critical"
                        ? "border-rose-500/20 bg-rose-500/5"
                        : item.severity === "warning"
                          ? "border-amber-500/20 bg-amber-500/5"
                          : "border-white/10 bg-black/20"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="text-sm font-semibold text-white">
                            {item.title}
                          </div>
                          <Badge
                            variant={
                              item.severity === "critical"
                                ? "error"
                                : item.severity === "warning"
                                  ? "warning"
                                  : "success"
                            }
                            size="sm"
                          >
                            {item.severity}
                          </Badge>
                        </div>
                        <div className="mt-2 text-sm leading-6 text-slate-300">
                          {item.message}
                        </div>
                        <div className="mt-2 text-[11px] uppercase tracking-[0.2em] text-slate-500">
                          {item.source} · {formatWhen(item.created_at)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-emerald-100">
                  No active alerts right now.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-cyan-200">
                <Mail className="h-5 w-5" />
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Email
                </div>
                <div className="mt-1 text-lg font-semibold text-white">
                  Alert delivery
                </div>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              <InfoRow
                label="Provider"
                value={alertDelivery?.provider ?? "resend"}
              />
              <InfoRow
                label="Enabled"
                value={String(Boolean(alertDelivery?.enabled))}
              />
              <InfoRow
                label="From"
                value={alertDelivery?.from_email ?? "FAIMATRIX <noreply@faimatrix.com>"}
              />
              <InfoRow
                label="Recipients"
                value={alertDelivery?.recipients?.join(", ") || "—"}
              />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                variant="secondary"
                onClick={() => void runAlertAction("alerts/send")}
                loading={alertActionLoading === "alerts/send"}
                leftIcon={<Mail className="h-4 w-4" />}
              >
                Send alerts email
              </Button>
              <Button
                variant="outline"
                onClick={() => void runAlertAction("alerts/test")}
                loading={alertActionLoading === "alerts/test"}
                leftIcon={<Bell className="h-4 w-4" />}
              >
                Send test email
              </Button>
            </div>

            <div className="mt-4 rounded-2xl border border-cyan-500/10 bg-cyan-500/5 p-4 text-sm text-cyan-50">
              This page is only for operational alerts and delivery.
              <div className="mt-3">
                <Link
                  href="/dashboard/admin"
                  className="inline-flex items-center rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-xs font-medium text-violet-100 transition-colors hover:bg-violet-500/20"
                >
                  Open admin overview
                </Link>
              </div>
            </div>

            {alertActionResult && (
              <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold text-white">
                    Delivery result
                  </div>
                  <Badge
                    variant={
                      alertActionResult.status === "error" ? "error" : "success"
                    }
                    size="sm"
                  >
                    {alertActionResult.status}
                  </Badge>
                </div>
                <div className="mt-2 text-sm text-slate-300">
                  {alertActionResult.message}
                </div>
                {alertActionResult.details && (
                  <pre className="mt-3 overflow-auto rounded-xl border border-white/10 bg-black/40 p-3 text-[11px] text-slate-300">
                    {JSON.stringify(alertActionResult.details, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

function StatusTile({
  label,
  value,
  meta,
  tone,
}: {
  label: string;
  value: string;
  meta?: string;
  tone?: "success" | "warning" | "neutral";
}) {
  const toneClass =
    tone === "success"
      ? "border-emerald-500/20 bg-emerald-500/5"
      : tone === "warning"
        ? "border-amber-500/20 bg-amber-500/5"
        : "border-white/10 bg-black/20";
  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-lg font-semibold text-white">{value}</div>
      {meta && <div className="mt-1 text-[11px] text-slate-500">{meta}</div>}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
        {label}
      </div>
      <div className="mt-1 break-all text-sm text-slate-200">{value}</div>
    </div>
  );
}
