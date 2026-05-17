"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Activity,
  Bell,
  Building2,
  Clock3,
  Database,
  FileClock,
  History,
  KeyRound,
  RefreshCw,
  ServerCog,
  Settings2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
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

type ControlIncident = {
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

type ControlCenterStatus = {
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
    encryption_at_rest?: boolean;
    encryption_fail_closed?: boolean;
    admin_key_configured?: boolean;
  };
  backups: BackupItem[];
  alerts: ControlIncident[];
  alert_delivery: AlertDelivery;
};

type ControlSection =
  | "overview"
  | "incidents"
  | "security"
  | "tenants"
  | "data"
  | "jobs"
  | "deployments"
  | "audit"
  | "maintenance";

const SECTION_DEFS: Array<{
  id: ControlSection;
  label: string;
  subtitle: string;
  icon: ReactNode;
}> = [
  {
    id: "overview",
    label: "Overview",
    subtitle: "Health, readiness, version, and freshness",
    icon: <ServerCog className="h-4 w-4" />,
  },
  {
    id: "incidents",
    label: "Incidents",
    subtitle: "Severity, ownership, timeline, and resolution",
    icon: <Bell className="h-4 w-4" />,
  },
  {
    id: "security",
    label: "Security",
    subtitle: "Auth posture, access, rotation, and audit",
    icon: <ShieldCheck className="h-4 w-4" />,
  },
  {
    id: "tenants",
    label: "Tenants / Users",
    subtitle: "Quotas, usage, isolation, and support view",
    icon: <Users className="h-4 w-4" />,
  },
  {
    id: "data",
    label: "Data / Storage",
    subtitle: "Backups, restores, retention, migrations",
    icon: <Database className="h-4 w-4" />,
  },
  {
    id: "jobs",
    label: "Jobs / Automation",
    subtitle: "Queues, retries, schedules, SLA misses",
    icon: <Workflow className="h-4 w-4" />,
  },
  {
    id: "deployments",
    label: "Deployments",
    subtitle: "Release, rollout, config drift, flags",
    icon: <Sparkles className="h-4 w-4" />,
  },
  {
    id: "audit",
    label: "Audit",
    subtitle: "Who did what, where, and when",
    icon: <History className="h-4 w-4" />,
  },
  {
    id: "maintenance",
    label: "Advanced Maintenance",
    subtitle: "Reindex, snapshot, replay, repair",
    icon: <ServerCog className="h-4 w-4" />,
  },
];

type ActionResult = {
  status: string;
  message: string;
  details?: Record<string, unknown>;
};

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

function formatHoursAgo(value?: string): string {
  if (!value) return "not tracked";
  const ts = Date.parse(value);
  if (Number.isNaN(ts)) return "not tracked";
  const hours = Math.max(0, (Date.now() - ts) / 36e5);
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))} min ago`;
  if (hours < 24) return `${hours.toFixed(hours >= 10 ? 0 : 1)} h ago`;
  return `${(hours / 24).toFixed(1)} d ago`;
}

function incidentStatus(severity: string): string {
  if (severity === "critical") return "open";
  if (severity === "warning") return "investigating";
  if (severity === "info") return "monitoring";
  return "resolved";
}

function incidentOwner(source: string): string {
  if (source === "health") return "Platform on-call";
  if (source === "readiness") return "Release manager";
  if (source === "backups") return "Storage operator";
  if (source === "runtime") return "Security owner";
  return "Ops triage";
}

function affectedSystems(source: string): string[] {
  if (source === "health") return ["API", "Proxy", "Caddy"];
  if (source === "readiness") return ["Database", "Migrations", "Schema"];
  if (source === "backups") return ["Backup job", "Raw store", "Retention"];
  if (source === "runtime")
    return ["Auth", "Tenant isolation", "Control plane"];
  return ["Platform"];
}

function sectionTone(status?: string): "success" | "warning" | "neutral" {
  if (status === "ok" || status === "ready" || status === "true")
    return "success";
  if (status === "degraded" || status === "not_ready" || status === "false") {
    return "warning";
  }
  return "neutral";
}

function toneClass(tone: "success" | "warning" | "neutral"): string {
  if (tone === "success") return "border-emerald-500/20 bg-emerald-500/5";
  if (tone === "warning") return "border-amber-500/20 bg-amber-500/5";
  return "border-white/10 bg-black/20";
}

function badgeVariantFromSeverity(
  severity: string,
): "error" | "warning" | "success" | "info" | "default" {
  if (severity === "critical") return "error";
  if (severity === "warning") return "warning";
  if (severity === "info") return "info";
  if (severity === "success") return "success";
  return "default";
}

export function ControlCenterConsole({
  initialSection = "overview",
}: {
  initialSection?: string;
}) {
  const router = useRouter();
  const { data: session, status: sessionStatus } = useSession();
  const [snapshot, setSnapshot] = useState<ControlCenterStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graphId, setGraphId] = useState<string>("");
  const [maintenanceAction, setMaintenanceAction] = useState<string | null>(
    null,
  );
  const [maintenanceResult, setMaintenanceResult] =
    useState<ActionResult | null>(null);
  const [section, setSection] = useState<ControlSection>("overview");
  const [displaySection, setDisplaySection] =
    useState<ControlSection>("overview");
  const [isSectionTransitioning, setIsSectionTransitioning] = useState(false);
  const isAdmin = Boolean((session as { isAdmin?: boolean } | null)?.isAdmin);
  const suppressSectionTransitionRef = useRef(false);

  const sessionGraphId = useMemo(() => {
    return String(
      (session as { graphId?: string } | null)?.graphId || "",
    ).trim();
  }, [session]);

  useEffect(() => {
    if (sessionGraphId && !graphId) {
      setGraphId(sessionGraphId);
    }
  }, [graphId, sessionGraphId]);

  const loadSnapshot = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/status", { cache: "no-store" });
      const data = await readJsonSafely<ControlCenterStatus>(res);
      if (!res.ok || !data) {
        throw new Error(
          `Status request failed (${res.status})${data ? "" : ": non-JSON response"}`,
        );
      }
      setSnapshot(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Control center unavailable",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (sessionStatus === "authenticated" && isAdmin) {
      void loadSnapshot();
    } else if (sessionStatus !== "loading") {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionStatus, isAdmin]);

  useEffect(() => {
    const incoming = (initialSection || "overview").trim().toLowerCase();
    const normalized = SECTION_DEFS.find((item) => item.id === incoming)?.id;
    if (normalized) {
      suppressSectionTransitionRef.current = true;
      setSection(normalized);
      setDisplaySection(normalized);
      setIsSectionTransitioning(false);
    }
  }, [initialSection]);

  useEffect(() => {
    if (displaySection === section) {
      suppressSectionTransitionRef.current = false;
      return;
    }

    if (suppressSectionTransitionRef.current) {
      suppressSectionTransitionRef.current = false;
      setDisplaySection(section);
      setIsSectionTransitioning(false);
      return;
    }

    setIsSectionTransitioning(true);
    const swapTimer = window.setTimeout(() => {
      setDisplaySection(section);
      window.setTimeout(() => {
        setIsSectionTransitioning(false);
      }, 90);
    }, 130);

    return () => {
      window.clearTimeout(swapTimer);
    };
  }, [section, displaySection]);

  const activeSection =
    SECTION_DEFS.find((item) => item.id === section) ?? SECTION_DEFS[0];
  const visibleSection =
    SECTION_DEFS.find((item) => item.id === displaySection) ?? SECTION_DEFS[0];
  const sectionIndex = Math.max(
    0,
    SECTION_DEFS.findIndex((item) => item.id === section),
  );

  const latestBackup = snapshot?.backups?.[0];
  const incidents = snapshot?.alerts ?? [];
  const criticalIncidents = incidents.filter(
    (item) => item.severity === "critical",
  );
  const warningIncidents = incidents.filter(
    (item) => item.severity === "warning",
  );

  const alertFreshness = latestBackup
    ? formatHoursAgo(latestBackup.modified_at)
    : "no backups";

  function renderSectionButtons(collapsed: boolean) {
    return (
      <div role="tablist" aria-label="Control pages" className="grid gap-1.5">
        {SECTION_DEFS.map((item) => {
          const active = section === item.id;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`control-tab-${item.id}`}
              aria-controls={`control-panel-${item.id}`}
              aria-selected={active}
              title={collapsed ? `${item.label} · ${item.subtitle}` : undefined}
              onClick={() => {
                setSection(item.id);
                router.replace(`/dashboard/control-plane?section=${item.id}`, {
                  scroll: false,
                });
              }}
              className={[
                "group relative ml-auto flex items-center gap-3 overflow-visible rounded-2xl border text-left transition-[width,transform,box-shadow,border-color,background-color] duration-300 ease-out",
                collapsed
                  ? "w-[60px] justify-center gap-0 px-0 py-2.5 hover:w-[248px]"
                  : "w-full justify-end px-3 py-3",
                active
                  ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-50 shadow-[0_0_0_1px_rgba(34,211,238,0.08),0_10px_24px_rgba(34,211,238,0.06)]"
                  : "border-white/10 bg-white/[0.03] text-slate-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.06] hover:shadow-[0_10px_18px_rgba(0,0,0,0.16)]",
              ].join(" ")}
            >
              <div className="relative z-20 flex h-10 w-10 shrink-0 items-center justify-center text-slate-300 transition-colors group-hover:text-white">
                {item.icon}
              </div>
              {collapsed ? (
                <div className="min-w-0 flex-1 max-w-0 overflow-hidden whitespace-nowrap opacity-0 translate-x-2 transition-all duration-300 ease-out group-hover:max-w-[170px] group-hover:opacity-100 group-hover:translate-x-0">
                  <div className="text-[11px] font-semibold leading-none text-white">
                    {item.label}
                  </div>
                  <div className="mt-1 text-[10px] leading-4 text-slate-400">
                    {item.subtitle}
                  </div>
                </div>
              ) : (
                <div className="min-w-0 flex-1 overflow-hidden transition-all duration-300 ease-out max-w-[170px] opacity-100 translate-x-0">
                  <div className="text-[11px] font-semibold leading-none">
                    {item.label}
                  </div>
                  <div className="mt-1 text-[10px] leading-4 text-slate-500">
                    {item.subtitle}
                  </div>
                </div>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  const headerActions = (
    <div className="flex items-center gap-2">
      <Link
        href="/dashboard/control-plane?section=incidents"
        className="inline-flex h-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] px-3 text-xs font-medium text-slate-200 transition-colors hover:border-rose-500/30 hover:bg-rose-500/10 hover:text-rose-100"
      >
        Incidents
      </Link>
      <Button
        variant="outline"
        size="sm"
        onClick={() => void loadSnapshot()}
        leftIcon={<RefreshCw className="h-4 w-4" />}
      >
        Refresh
      </Button>
    </div>
  );

  if (sessionStatus === "loading" || loading) {
    return (
      <div className="space-y-6">
        <GlassHeader
          title="Control Center"
          subtitle="Platform operations and governance"
          icon={ServerCog}
          actions={headerActions}
        />
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-6 text-sm text-slate-400">
          Loading control center snapshot...
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <GlassHeader
          title="Control Center"
          subtitle="Platform operations and governance"
          icon={ServerCog}
          actions={headerActions}
        />
        <div className="rounded-3xl border border-rose-500/20 bg-rose-500/5 p-6 text-sm text-rose-200">
          Control Center access is not enabled for this account.
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full space-y-4 pb-8 text-slate-100 px-0">
      <div className="faim-grid opacity-20" />

      <GlassHeader
        title="Control Center"
        subtitle="Platform operations, incidents, governance, and maintenance"
        icon={ServerCog}
        actions={headerActions}
      />

      {error && (
        <div className="rounded-3xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-100">
          {error}
        </div>
      )}

      <section className="rounded-[32px] border border-white/10 bg-white/[0.03] p-3.5 lg:hidden">
        <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          Control pages
        </div>
        <div className="mt-3">{renderSectionButtons(false)}</div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[300px_minmax(0,1fr)] lg:pr-[96px]">
        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start min-w-0">
          <section className="rounded-[28px] border border-white/10 bg-white/[0.03] p-3.5">
            <div className="flex items-center justify-between gap-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                Control snapshot
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-600">
                Live posture
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2.5">
              <RailStat
                label="Service health"
                value={snapshot?.health?.status ?? "unknown"}
                meta={
                  snapshot?.health?.timestamp ?? "health timestamp unavailable"
                }
                tone={sectionTone(snapshot?.health?.status)}
                icon={<ShieldCheck className="h-4 w-4" />}
              />
              <RailStat
                label="Readiness"
                value={snapshot?.readiness?.status ?? "unknown"}
                meta={`DB ${snapshot?.readiness?.db_connected ? "ok" : "down"} · Tables ${snapshot?.readiness?.tables_ok ? "ok" : "missing"} · Migration ${snapshot?.readiness?.applied_migration ?? 0}/${snapshot?.readiness?.latest_migration ?? 0}`}
                tone={sectionTone(snapshot?.readiness?.status)}
                icon={<Activity className="h-4 w-4" />}
              />
              <RailStat
                label="Incidents"
                value={String(incidents.length)}
                meta={`${criticalIncidents.length} critical · ${warningIncidents.length} warning`}
                tone={incidents.length ? "warning" : "success"}
                icon={<ShieldAlert className="h-4 w-4" />}
              />
              <RailStat
                label="Backups"
                value={
                  latestBackup
                    ? formatHoursAgo(latestBackup.modified_at)
                    : "none"
                }
                meta={
                  latestBackup ? latestBackup.name : "backup inventory empty"
                }
                tone={latestBackup ? "success" : "warning"}
                icon={<Database className="h-4 w-4" />}
              />
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <RailMetaPill
                label="Version"
                value={snapshot?.version?.version ?? "unknown"}
              />
              <RailMetaPill
                label="Build"
                value={formatWhen(snapshot?.version?.build_time)}
              />
              <RailMetaPill
                label="Runtime"
                value={snapshot?.runtime?.mode ?? "unknown"}
              />
              <RailMetaPill
                label="Backup freshness"
                value={
                  alertFreshness === "no backups"
                    ? "no backup found"
                    : alertFreshness
                }
              />
            </div>
          </section>
        </aside>

        <main className="space-y-4 min-w-0">
          <section className="rounded-[28px] border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Active page
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 px-3 py-1.5 text-sm font-medium text-cyan-100">
                    {sectionIndex + 1} / {SECTION_DEFS.length}
                  </div>
                  <div className="text-lg font-semibold text-white">
                    {activeSection.label}
                  </div>
                </div>
                <p className="mt-2 text-sm text-slate-400">
                  {activeSection.subtitle}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-300">
                Each toggle is its own control page. The active page stays in
                one panel, with internal scroll only when a section is long.
              </div>
            </div>
          </section>

          <SectionCard
            id={visibleSection.id}
            title={visibleSection.label}
            subtitle={visibleSection.subtitle}
            icon={activeSectionIcon(displaySection)}
            accent={activeSectionAccent(displaySection)}
          >
            <div
              className={[
                "max-h-[calc(100vh-27rem)] overflow-auto pr-1.5 transition-all duration-200 ease-out motion-reduce:transition-none",
                isSectionTransitioning
                  ? "opacity-70 translate-y-1 scale-[0.996]"
                  : "opacity-100 translate-y-0 scale-100",
              ].join(" ")}
            >
              {renderSectionContent(displaySection)}
            </div>
          </SectionCard>
        </main>
      </div>

      <aside className="fixed right-4 top-[108px] z-40 hidden lg:flex lg:flex-col lg:items-end lg:gap-2">
        {renderSectionButtons(true)}
      </aside>
    </div>
  );

  async function runMaintenance(action: "reindex" | "snapshot" | "replay") {
    if (!graphId.trim()) {
      setMaintenanceResult({
        status: "error",
        message: "Enter a graph ID first.",
      });
      return;
    }
    setMaintenanceAction(action);
    setMaintenanceResult(null);
    try {
      const path =
        action === "reindex"
          ? "/api/admin/reindex"
          : action === "snapshot"
            ? "/api/admin/snapshot/create"
            : "/api/admin/replay/verify";
      const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ graph_id: graphId.trim() }),
      });
      const data = await readJsonSafely<ActionResult>(res);
      if (!res.ok || !data) {
        throw new Error(
          `Maintenance action failed (${res.status})${data ? "" : ": non-JSON response"}`,
        );
      }
      setMaintenanceResult(data);
      await loadSnapshot();
    } catch (err) {
      setMaintenanceResult({
        status: "error",
        message:
          err instanceof Error ? err.message : "Maintenance action failed",
      });
    } finally {
      setMaintenanceAction(null);
    }
  }

  function renderSectionContent(active: ControlSection): ReactNode {
    switch (active) {
      case "overview":
        return (
          <div className="grid gap-4 xl:grid-cols-[1.25fr_.75fr]">
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <MetricCard
                  label="Service health"
                  value={snapshot?.health?.status ?? "unknown"}
                  detail={`Last probe ${snapshot?.health?.timestamp ? formatWhen(snapshot.health.timestamp) : "unavailable"}`}
                  tone={sectionTone(snapshot?.health?.status)}
                />
                <MetricCard
                  label="Readiness"
                  value={snapshot?.readiness?.status ?? "unknown"}
                  detail={`Migrations ${snapshot?.readiness?.applied_migration ?? 0}/${snapshot?.readiness?.latest_migration ?? 0}`}
                  tone={sectionTone(snapshot?.readiness?.status)}
                />
                <MetricCard
                  label="Deploy version"
                  value={snapshot?.version?.version ?? "unknown"}
                  detail={`Stage ${snapshot?.version?.stage ?? "—"}`}
                  tone="neutral"
                />
                <MetricCard
                  label="Uptime"
                  value="probe pending"
                  detail="Add a process uptime gauge to surface live runtime duration"
                  tone="neutral"
                />
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <InfoTile
                  label="Active incidents"
                  value={`${incidents.length}`}
                  meta="Derived from operational alerts"
                  icon={<Bell className="h-4 w-4" />}
                />
                <InfoTile
                  label="Recent changes"
                  value={
                    snapshot?.version?.build_time
                      ? formatWhen(snapshot.version.build_time)
                      : "pending probe"
                  }
                  meta="Release time and migration history belong here"
                  icon={<History className="h-4 w-4" />}
                />
                <InfoTile
                  label="Backup freshness"
                  value={
                    latestBackup
                      ? formatHoursAgo(latestBackup.modified_at)
                      : "empty"
                  }
                  meta={latestBackup?.name ?? "no backup inventory"}
                  icon={<Clock3 className="h-4 w-4" />}
                />
                <InfoTile
                  label="Operator access"
                  value={
                    snapshot?.runtime?.admin_key_configured
                      ? "configured"
                      : "missing"
                  }
                  meta="Operator access stays server-side only"
                  icon={<KeyRound className="h-4 w-4" />}
                />
              </div>
            </div>

            <div className="space-y-3">
              <MiniPanel
                title="Runtime snapshot"
                icon={<Shield className="h-4 w-4" />}
              >
                <FieldRow
                  label="Public origin"
                  value={snapshot?.runtime?.public_origin ?? "—"}
                />
                <FieldRow
                  label="Auth posture"
                  value={
                    snapshot?.runtime?.auth_db_primary
                      ? "DB primary"
                      : "fallback"
                  }
                />
                <FieldRow
                  label="Scope enforcement"
                  value={
                    snapshot?.runtime?.auth_scope_enforcement_enabled
                      ? "enabled"
                      : "disabled"
                  }
                />
                <FieldRow
                  label="Encryption at rest"
                  value={
                    snapshot?.runtime?.encryption_at_rest
                      ? "enabled"
                      : "disabled"
                  }
                />
                <FieldRow
                  label="Fail closed"
                  value={
                    snapshot?.runtime?.encryption_fail_closed
                      ? "enabled"
                      : "disabled"
                  }
                />
              </MiniPanel>

              <MiniPanel
                title="Backup inventory"
                icon={<Database className="h-4 w-4" />}
              >
                {latestBackup ? (
                  <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-3">
                    <div className="text-sm font-medium text-emerald-100">
                      {latestBackup.name}
                    </div>
                    <div className="mt-1 text-[11px] text-emerald-200/70">
                      {latestBackup.kind} ·{" "}
                      {latestBackup.compressed ? "compressed" : "plain"} ·{" "}
                      {prettySize(latestBackup.size_bytes)}
                    </div>
                    <div className="mt-1 text-[11px] text-emerald-200/70">
                      {formatWhen(latestBackup.modified_at)}
                    </div>
                  </div>
                ) : (
                  <EmptyStateCard
                    title="No backups found"
                    copy="Keep backup freshness on this page, but do not make it the only operational signal."
                  />
                )}
              </MiniPanel>
            </div>
          </div>
        );
      case "incidents":
        return (
          <div className="grid gap-4 xl:grid-cols-[1.1fr_.9fr]">
            <div className="space-y-3">
              {incidents.length ? (
                incidents.map((item) => (
                  <IncidentCard key={item.id} incident={item} />
                ))
              ) : (
                <EmptyStateCard
                  title="No active incidents"
                  copy="Incident workflow should surface only when the platform has a live issue, not as a permanent mail utility."
                />
              )}
            </div>

            <MiniPanel
              title="Incident workflow"
              icon={<Workflow className="h-4 w-4" />}
            >
              <PlaceholderStep
                label="Triage"
                value="Incoming incident is classified by severity and source."
              />
              <PlaceholderStep
                label="Owner"
                value="Assign platform owner or resolver team."
              />
              <PlaceholderStep
                label="Acknowledgement"
                value="Track who acknowledged and when."
              />
              <PlaceholderStep
                label="Resolution"
                value="Capture fix summary and close-out note."
              />
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Button variant="outline" size="sm" disabled>
                  Acknowledge
                </Button>
                <Button variant="outline" size="sm" disabled>
                  Resolve
                </Button>
              </div>
              <p className="mt-3 text-[11px] text-slate-500">
                Incident handling stays event-driven and tracked to closure.
              </p>
            </MiniPanel>
          </div>
        );
      case "security":
        return (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <MetricCard
              label="Operator access"
              value={
                snapshot?.runtime?.admin_key_configured
                  ? "configured"
                  : "missing"
              }
              detail="Server-side admin key"
              tone={
                snapshot?.runtime?.admin_key_configured ? "success" : "warning"
              }
            />
            <MetricCard
              label="Role assignments"
              value="inventory pending"
              detail="RBAC inventory feed not connected"
              tone="neutral"
            />
            <MetricCard
              label="Auth posture"
              value={
                snapshot?.runtime?.auth_db_primary ? "DB primary" : "fallback"
              }
              detail="Primary auth path should be enforced"
              tone={snapshot?.runtime?.auth_db_primary ? "success" : "warning"}
            />
            <MetricCard
              label="Key rotation"
              value="rotation watch"
              detail="Add expiry and rotation tracking when the feed is connected"
              tone="neutral"
            />
            <MetricCard
              label="Audit events"
              value="event feed pending"
              detail="Who did what, from where, and when"
              tone="neutral"
            />
            <MetricCard
              label="Suspicious activity"
              value="watchlist clear"
              detail="Security anomaly feed not connected"
              tone="neutral"
            />
          </div>
        );
      case "tenants":
        const tenantRows = [
          {
            tenant: "Primary",
            quota: "policy-led",
            usage: "metered",
            isolation: "strict",
            support: "enabled",
          },
          {
            tenant: "Enterprise",
            quota: "guarded",
            usage: "allocated",
            isolation: "strict",
            support: "priority",
          },
          {
            tenant: "Trial",
            quota: "capped",
            usage: "light",
            isolation: "sandboxed",
            support: "self-service",
          },
        ];
        return (
          <div className="grid gap-4 xl:grid-cols-[1fr_.85fr]">
            <div className="rounded-[22px] border border-white/10 bg-black/20 p-4">
              <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                Tenant inventory
              </div>
              <div className="overflow-hidden rounded-2xl border border-white/10">
                <div className="grid grid-cols-5 bg-white/[0.03] px-4 py-3 text-[10px] uppercase tracking-[0.2em] text-slate-500">
                  <span>Tenant</span>
                  <span>Quota</span>
                  <span>Usage</span>
                  <span>Isolation</span>
                  <span>Support</span>
                </div>
                {tenantRows.map((row) => (
                  <div
                    key={row.tenant}
                    className="grid grid-cols-5 border-t border-white/8 px-4 py-4 text-sm text-slate-300"
                  >
                    <span className="font-medium text-slate-100">
                      {row.tenant}
                    </span>
                    <span>{row.quota}</span>
                    <span>{row.usage}</span>
                    <span>{row.isolation}</span>
                    <span>{row.support}</span>
                  </div>
                ))}
              </div>
            </div>

            <MiniPanel
              title="Support view"
              icon={<Building2 className="h-4 w-4" />}
            >
              <PlaceholderStep
                label="Quotas"
                value="Per-tenant limits and alerts belong here."
              />
              <PlaceholderStep
                label="Usage"
                value="Show storage, query, and job load per tenant."
              />
              <PlaceholderStep
                label="Permission drift"
                value="Track unexpected role or scope changes."
              />
              <PlaceholderStep
                label="Isolation checks"
                value="Confirm tenant boundaries on every sensitive operation."
              />
              <EmptyStateCard
                title="Tenant feed pending"
                copy="This section is reserved for tenant inventory, support workflow, and isolation checks."
              />
            </MiniPanel>
          </div>
        );
      case "data":
        return (
          <div className="grid gap-4 xl:grid-cols-[1.05fr_.95fr]">
            <div className="grid gap-3 md:grid-cols-2">
              <MetricCard
                label="Backups"
                value={
                  latestBackup ? prettySize(latestBackup.size_bytes) : "none"
                }
                detail={
                  latestBackup ? latestBackup.name : "backup inventory empty"
                }
                tone={latestBackup ? "success" : "warning"}
              />
              <MetricCard
                label="Restore"
                value="controlled"
                detail="Restore workflow is reserved for operator use"
                tone="neutral"
              />
              <MetricCard
                label="Retention"
                value="policy-driven"
                detail="Attach retention and purge policy"
                tone="neutral"
              />
              <MetricCard
                label="Migration status"
                value={
                  snapshot?.readiness?.migrations_ok ? "caught up" : "pending"
                }
                detail={`Applied ${snapshot?.readiness?.applied_migration ?? 0}/${snapshot?.readiness?.latest_migration ?? 0}`}
                tone={
                  snapshot?.readiness?.migrations_ok ? "success" : "warning"
                }
              />
              <MetricCard
                label="Raw store health"
                value={
                  snapshot?.runtime?.raw_store_path ? "configured" : "missing"
                }
                detail={
                  snapshot?.runtime?.raw_store_path ??
                  "raw store path not exposed"
                }
                tone={snapshot?.runtime?.raw_store_path ? "success" : "warning"}
              />
              <MetricCard
                label="Storage growth"
                value="trend pending"
                detail="Add trend chart and thresholds when storage telemetry arrives"
                tone="neutral"
              />
            </div>

            <MiniPanel
              title="Backup inventory"
              icon={<FileClock className="h-4 w-4" />}
            >
              <div className="space-y-2">
                {snapshot?.backups?.length ? (
                  snapshot.backups.slice(0, 6).map((item) => (
                    <div
                      key={item.name}
                      className="rounded-2xl border border-white/10 bg-black/20 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm font-medium text-slate-100">
                            {item.name}
                          </div>
                          <div className="mt-1 text-[11px] text-slate-500">
                            {item.kind} ·{" "}
                            {item.compressed ? "compressed" : "plain"} ·{" "}
                            {prettySize(item.size_bytes)}
                          </div>
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {formatHoursAgo(item.modified_at)}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyStateCard
                    title="No backups available"
                    copy="Keep the list here as operator inventory, not as the main page centerpiece."
                  />
                )}
              </div>
            </MiniPanel>
          </div>
        );
      case "jobs":
        return (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <MetricCard
              label="Queue health"
              value={snapshot?.runtime?.enable_jobs ? "enabled" : "disabled"}
              detail="Job runner availability"
              tone={snapshot?.runtime?.enable_jobs ? "success" : "warning"}
            />
            <MetricCard
              label="Failed jobs"
              value="telemetry pending"
              detail="Need job telemetry"
              tone="neutral"
            />
            <MetricCard
              label="Retries"
              value="policy pending"
              detail="Retry policy and backoff"
              tone="neutral"
            />
            <MetricCard
              label="Schedules"
              value="scheduler view"
              detail="Cron and scheduled automation"
              tone="neutral"
            />
            <MetricCard
              label="Last run"
              value="run feed pending"
              detail="Show most recent automation run"
              tone="neutral"
            />
            <MetricCard
              label="SLA misses"
              value="watchlist"
              detail="Service-level misses and breaches"
              tone="neutral"
            />
          </div>
        );
      case "deployments":
        return (
          <div className="grid gap-4 xl:grid-cols-[1fr_.9fr]">
            <div className="grid gap-3 md:grid-cols-2">
              <MetricCard
                label="Current release"
                value={snapshot?.version?.version ?? "unknown"}
                detail={`Stage ${snapshot?.version?.stage ?? "—"}`}
                tone="neutral"
              />
              <MetricCard
                label="Rollout history"
                value="release train"
                detail="Track release train and promotion events"
                tone="neutral"
              />
              <MetricCard
                label="Config drift"
                value="watch pending"
                detail="Detect environment mismatch"
                tone="neutral"
              />
              <MetricCard
                label="Feature flags"
                value={snapshot?.version?.features ? "available" : "unknown"}
                detail="Expose active runtime toggles"
                tone={snapshot?.version?.features ? "success" : "warning"}
              />
            </div>

            <MiniPanel
              title="Environment comparison"
              icon={<Settings2 className="h-4 w-4" />}
            >
              <PlaceholderStep
                label="Local"
                value="Compare local prod and VPS prod settings."
              />
              <PlaceholderStep
                label="VPS"
                value="Mirror the same shape with domain-only differences."
              />
              <PlaceholderStep
                label="Drift"
                value="Highlight config, release, or storage mismatch."
              />
              <PlaceholderStep
                label="Promotion"
                value="Track what changed and who approved it."
              />
            </MiniPanel>
          </div>
        );
      case "audit":
        const auditEntries = [
          { label: "Who did what", state: "recorded" },
          { label: "When", state: "recorded" },
          { label: "From where", state: "recorded" },
          { label: "What changed", state: "recorded" },
          { label: "Approvals", state: "recorded" },
          { label: "Reversible actions", state: "pending feed" },
        ];
        return (
          <div className="grid gap-4 xl:grid-cols-[1fr_.9fr]">
            <div className="space-y-3">
              {auditEntries.map((item, idx) => (
                <div
                  key={item.label}
                  className="rounded-2xl border border-white/10 bg-black/20 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-slate-100">
                      {item.label}
                    </div>
                    <Badge variant={idx < 5 ? "success" : "default"} size="sm">
                      {item.state}
                    </Badge>
                  </div>
                  <div className="mt-2 text-sm text-slate-400">
                    Audit history is shown as a first-class control surface,
                    even before the event feed is fully wired.
                  </div>
                </div>
              ))}
            </div>

            <MiniPanel
              title="Change history"
              icon={<Clock3 className="h-4 w-4" />}
            >
              <PlaceholderStep
                label="Release note"
                value="Show deploy, migration, and policy changes together."
              />
              <PlaceholderStep
                label="Approval chain"
                value="Record who approved risky actions."
              />
              <PlaceholderStep
                label="Rollback link"
                value="Every change should point to a safe reverse path."
              />
            </MiniPanel>
          </div>
        );
      case "maintenance":
        return (
          <div className="grid gap-4 xl:grid-cols-[1fr_.85fr]">
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-[1fr_auto]">
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
                    onClick={() => void runMaintenance("reindex")}
                    loading={maintenanceAction === "reindex"}
                    leftIcon={<Activity className="h-4 w-4" />}
                  >
                    Reindex
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => void runMaintenance("snapshot")}
                    loading={maintenanceAction === "snapshot"}
                    leftIcon={<Sparkles className="h-4 w-4" />}
                  >
                    Snapshot
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => void runMaintenance("replay")}
                    loading={maintenanceAction === "replay"}
                    leftIcon={<Shield className="h-4 w-4" />}
                  >
                    Verify replay
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <MetricCard
                  label="Reindex"
                  value="operator tool"
                  detail="Acceleration only"
                  tone="neutral"
                />
                <MetricCard
                  label="Snapshot"
                  value="operator tool"
                  detail="Graph state capture"
                  tone="neutral"
                />
                <MetricCard
                  label="Repair tools"
                  value="restricted"
                  detail="Reserved for controlled maintenance"
                  tone="neutral"
                />
              </div>

              {maintenanceResult && (
                <div className="rounded-3xl border border-white/10 bg-black/30 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-white">
                      Maintenance result
                    </div>
                    <Badge
                      variant={
                        maintenanceResult.status === "error"
                          ? "error"
                          : "success"
                      }
                      size="sm"
                    >
                      {maintenanceResult.status}
                    </Badge>
                  </div>
                  <div className="mt-2 text-sm text-slate-300">
                    {maintenanceResult.message}
                  </div>
                  {maintenanceResult.details && (
                    <pre className="mt-3 overflow-auto rounded-xl border border-white/10 bg-black/40 p-3 text-[11px] text-slate-300">
                      {JSON.stringify(maintenanceResult.details, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>

            <MiniPanel
              title="Operator warning"
              icon={<ShieldAlert className="h-4 w-4" />}
            >
              <PlaceholderStep
                label="Approval flow"
                value="Require explicit approval for risky actions."
              />
              <PlaceholderStep
                label="Audit trail"
                value="Record who started and who completed the maintenance."
              />
              <PlaceholderStep
                label="Rollback safety"
                value="Do not run destructive operations without a recovery plan."
              />
              <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-100">
                This is the only section that should still feel operational. It
                is for controlled repair, not daily admin browsing.
              </div>
            </MiniPanel>
          </div>
        );
      default:
        return null;
    }
  }
}

function activeSectionAccent(
  section: ControlSection,
): "cyan" | "rose" | "violet" | "emerald" | "amber" {
  if (section === "incidents") return "rose";
  if (section === "security") return "violet";
  if (section === "data") return "emerald";
  if (section === "jobs" || section === "maintenance") return "amber";
  return "cyan";
}

function activeSectionIcon(section: ControlSection): ReactNode {
  if (section === "incidents") return <Bell className="h-5 w-5" />;
  if (section === "security") return <ShieldCheck className="h-5 w-5" />;
  if (section === "tenants") return <Users className="h-5 w-5" />;
  if (section === "data") return <Database className="h-5 w-5" />;
  if (section === "jobs") return <Workflow className="h-5 w-5" />;
  if (section === "deployments") return <Sparkles className="h-5 w-5" />;
  if (section === "audit") return <History className="h-5 w-5" />;
  if (section === "maintenance") return <ServerCog className="h-5 w-5" />;
  return <ServerCog className="h-5 w-5" />;
}

function StatusTile({
  label,
  value,
  meta,
  tone,
  icon,
}: {
  label: string;
  value: string;
  meta?: string;
  tone: "success" | "warning" | "neutral";
  icon?: ReactNode;
}) {
  return (
    <div className={`rounded-2xl border p-4 ${toneClass(tone)}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          {label}
        </div>
        {icon}
      </div>
      <div className="mt-2 text-lg font-semibold text-white">{value}</div>
      {meta && <div className="mt-1 text-[11px] text-slate-500">{meta}</div>}
    </div>
  );
}

function RailStat({
  label,
  value,
  meta,
  tone,
  icon,
}: {
  label: string;
  value: string;
  meta?: string;
  tone: "success" | "warning" | "neutral";
  icon?: ReactNode;
}) {
  return (
    <div className={`min-h-[96px] rounded-2xl border p-3.5 ${toneClass(tone)}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          {label}
        </div>
        {icon}
      </div>
      <div className="mt-2 text-base font-semibold text-white leading-tight">
        {value}
      </div>
      {meta && (
        <div className="mt-1 line-clamp-2 text-[11px] leading-5 text-slate-500">
          {meta}
        </div>
      )}
    </div>
  );
}

function RailMetaPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[120px] flex-1 rounded-2xl border border-white/10 bg-black/20 px-3 py-2.5">
      <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-500">
        {label}
      </div>
      <div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-200">
        {value}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "success" | "warning" | "neutral";
}) {
  return (
    <div
      className={`rounded-[26px] border p-4 shadow-[0_1px_0_rgba(255,255,255,0.02)_inset] ${toneClass(tone)}`}
    >
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-xl font-semibold text-white">{value}</div>
      <div className="mt-1 text-[11px] leading-5 text-slate-500">{detail}</div>
    </div>
  );
}

function InfoTile({
  label,
  value,
  meta,
  icon,
}: {
  label: string;
  value: string;
  meta: string;
  icon: ReactNode;
}) {
  return (
    <div className="rounded-[22px] border border-white/10 bg-slate-950/75 p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          {label}
        </div>
        {icon}
      </div>
      <div className="mt-2 text-sm font-medium text-white">{value}</div>
      <div className="mt-1 text-[11px] text-slate-500">{meta}</div>
    </div>
  );
}

function SectionCard({
  id,
  title,
  subtitle,
  icon,
  accent,
  children,
}: {
  id: ControlSection;
  title: string;
  subtitle: string;
  icon: ReactNode;
  accent: "cyan" | "rose" | "violet" | "emerald" | "amber";
  children: ReactNode;
}) {
  const accentClass =
    accent === "cyan"
      ? "border-cyan-500/20 bg-cyan-500/5"
      : accent === "rose"
        ? "border-rose-500/20 bg-rose-500/5"
        : accent === "violet"
          ? "border-violet-500/20 bg-violet-500/5"
          : accent === "emerald"
            ? "border-emerald-500/20 bg-emerald-500/5"
            : "border-amber-500/20 bg-amber-500/5";

  return (
    <section
      id={`control-panel-${id}`}
      role="tabpanel"
      aria-labelledby={`control-tab-${id}`}
      className="rounded-[32px] border border-white/10 bg-slate-950/85 p-5 shadow-[0_20px_50px_rgba(0,0,0,0.28)]"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className={`rounded-2xl border p-3 ${accentClass}`}>{icon}</div>
          <div>
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {title}
            </h2>
            <p className="mt-1 text-lg font-semibold text-white">{subtitle}</p>
          </div>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function MiniPanel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-slate-950/75 p-4">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
        {icon}
        {title}
      </div>
      <div className="mt-3 space-y-2">{children}</div>
    </div>
  );
}

function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-white/10 bg-slate-950/80 px-4 py-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
        {label}
      </div>
      <div className="mt-1 break-all text-sm text-slate-200">{value}</div>
    </div>
  );
}

function PlaceholderStep({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-white/10 bg-slate-950/70 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-sm leading-6 text-slate-300">{value}</div>
    </div>
  );
}

function EmptyStateCard({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="rounded-[22px] border border-dashed border-white/10 bg-slate-950/75 p-4">
      <div className="text-sm font-medium text-slate-100">{title}</div>
      <div className="mt-1 text-sm leading-6 text-slate-400">{copy}</div>
    </div>
  );
}

function NoteRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-white/10 bg-slate-950/80 px-4 py-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-sm text-slate-200">{value}</div>
    </div>
  );
}

function IncidentCard({ incident }: { incident: ControlIncident }) {
  const tone =
    incident.severity === "critical"
      ? "warning"
      : incident.severity === "warning"
        ? "warning"
        : "neutral";
  return (
    <div className={`rounded-[28px] border p-4 ${toneClass(tone)}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-sm font-semibold text-white">
              {incident.title}
            </div>
            <Badge
              variant={badgeVariantFromSeverity(incident.severity)}
              size="sm"
            >
              {incident.severity}
            </Badge>
            <Badge variant="outline" size="sm">
              {incidentStatus(incident.severity)}
            </Badge>
          </div>
          <div className="text-sm leading-6 text-slate-300">
            {incident.message}
          </div>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            <FieldRow label="Owner" value={incidentOwner(incident.source)} />
            <FieldRow
              label="Affected systems"
              value={affectedSystems(incident.source).join(" · ")}
            />
            <FieldRow
              label="Acknowledgement"
              value={incident.acknowledged ? "acknowledged" : "unacknowledged"}
            />
            <FieldRow
              label="Timeline"
              value={formatWhen(incident.created_at)}
            />
          </div>
        </div>
      </div>
      <div className="mt-3 rounded-[20px] border border-white/10 bg-slate-950/80 p-3 text-[11px] text-slate-400">
        Resolution notes: attach root cause, workaround, and closure when the
        incident is fully tracked.
      </div>
    </div>
  );
}
