"use client";

import React from "react";
import { RefreshCw } from "lucide-react";

interface DashboardHeaderProps {
  greeting: { text: string; emoji: string };
  isHealthy: boolean;
  version?: string;
  refreshing: boolean;
  onRefresh: () => void;
  tenantId?: string;
}

export function DashboardHeader({
  greeting,
  isHealthy,
  version,
  refreshing,
  onRefresh,
  tenantId,
}: DashboardHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <span>{greeting.emoji}</span>
            <span>{greeting.text}!</span>
          </h1>
          {tenantId && (
            <div className="px-2 py-0.5 rounded-md bg-[var(--faim-primary-muted)] text-[var(--faim-primary)] text-[10px] font-bold uppercase tracking-widest border border-[var(--faim-primary)]/20 shadow-[0_0_10px_rgba(34,211,238,0.1)]">
              Secure Tenant: {tenantId}
            </div>
          )}
        </div>
        <p className="text-[var(--text-secondary)] text-sm mt-1 max-w-lg">
          FAIM-Native Engine is operational. Multi-tenant isolation is active
          and hard-scoped to your secure environment.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="p-2 rounded-lg text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--glass-hover)] transition-colors disabled:opacity-50"
          title="Refresh (R)"
        >
          <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
        </button>
        <HealthBadge healthy={isHealthy} version={version} />
      </div>
    </header>
  );
}

function HealthBadge({
  healthy,
  version,
}: {
  healthy: boolean;
  version?: string;
}) {
  return (
    <div
      className={[
        "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
        "border transition-all",
        healthy
          ? "bg-[var(--faim-success-muted)] text-[var(--faim-success)] border-[var(--faim-success)]/30 shadow-[var(--glow-success)]"
          : "bg-[var(--faim-error-muted)] text-[var(--faim-error)] border-[var(--faim-error)]/30 shadow-[var(--glow-error)]",
      ].join(" ")}
    >
      <span
        className={[
          "w-2 h-2 rounded-full",
          healthy
            ? "bg-[var(--faim-success)] animate-pulse"
            : "bg-[var(--faim-error)]",
        ].join(" ")}
      />
      {healthy ? "Healthy" : "Offline"}
      {version && (
        <span className="text-[var(--text-tertiary)]">v{version}</span>
      )}
    </div>
  );
}
