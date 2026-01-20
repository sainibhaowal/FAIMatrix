"use client";

import React from "react";
import { MessageSquare, FileText, Network, Zap, TrendingUp, TrendingDown } from "lucide-react";
import { Card } from "@/components/ui";

interface DashboardMetricsProps {
  dimensionD: number;
  entropyH: number;
  nodesCount: number;
  edgeCount: number;
}

export function DashboardMetrics({
  dimensionD,
  entropyH,
  nodesCount,
  edgeCount,
}: DashboardMetricsProps) {
  return (
    <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        icon={<Activity size={20} />}
        label="Dimension (D)"
        value={dimensionD.toFixed(3)}
        trend={2.4}
        color="cyan"
      />
      <MetricCard
        icon={<Network size={20} />}
        label="Entropy (H)"
        value={entropyH.toFixed(3)}
        trend={-0.5}
        color="violet"
      />
      <MetricCard
        icon={<TrendingUp size={20} />}
        label="Total Nodes"
        value={nodesCount}
        color="pink"
      />
      <MetricCard
        icon={<Zap size={20} />}
        label="Total Edges"
        value={edgeCount}
        color="amber"
      />
    </section>
  );
}

function MetricCard({
  icon,
  label,
  value,
  trend,
  suffix = "",
  color = "cyan",
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  trend?: number;
  suffix?: string;
  color?: "cyan" | "violet" | "pink" | "amber";
}) {
  const colorMap = {
    cyan: {
      bg: "bg-[var(--faim-primary-muted)]",
      text: "text-[var(--faim-primary)]",
      glow: "shadow-[var(--glow-cyan)]",
    },
    violet: {
      bg: "bg-[var(--faim-secondary-muted)]",
      text: "text-[var(--faim-secondary)]",
      glow: "shadow-[var(--glow-violet)]",
    },
    pink: {
      bg: "bg-[var(--faim-accent)]/15",
      text: "text-[var(--faim-accent)]",
      glow: "shadow-[0_0_20px_rgba(244,114,182,0.15)]",
    },
    amber: {
      bg: "bg-[var(--faim-warning-muted)]",
      text: "text-[var(--faim-warning)]",
      glow: "shadow-[0_0_20px_rgba(251,191,36,0.15)]",
    },
  };

  const colors = colorMap[color];

  return (
    <Card interactive className="group">
      <div className="flex items-start justify-between">
        <div
          className={[
            "p-2.5 rounded-xl",
            colors.bg,
            colors.text,
            colors.glow,
            "transition-transform group-hover:scale-110",
          ].join(" ")}
        >
          {icon}
        </div>
        {typeof trend === "number" && (
          <div
            className={[
              "flex items-center gap-0.5 text-xs font-medium",
              trend >= 0 ? "text-[var(--faim-success)]" : "text-[var(--faim-error)]",
            ].join(" ")}
          >
            {trend >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>
      <div className="mt-3">
        <div className="text-2xl font-bold text-[var(--text-primary)]">
          {typeof value === "number" ? value.toLocaleString() : value}
          {suffix && <span className="text-sm font-normal text-[var(--text-secondary)]">{suffix}</span>}
        </div>
        <div className="text-xs text-[var(--text-secondary)] mt-0.5">{label}</div>
      </div>
    </Card>
  );
}
