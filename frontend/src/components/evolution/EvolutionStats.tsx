"use client";

import React from "react";
import { Dna, GitMerge, Scissors, TrendingUp } from "lucide-react";
import { GlowCard } from "@/components/ui/GlowCard";

type EvolutionEvent = {
  id: string;
  event_type: "merge" | "prune" | "promotion" | "evolution";
  timestamp: string;
  details?: {
    nodes_affected?: number;
    redundancy_reduced?: number;
    message?: string;
  };
};

interface EvolutionStatsProps {
  evolutionCount: number;
  events: EvolutionEvent[];
}

export function EvolutionStats({ evolutionCount, events }: EvolutionStatsProps) {
  const mergeCount = events.filter((e) => e.event_type === "merge").length;
  const pruneCount = events.filter((e) => e.event_type === "prune").length;
  const promotionCount = events.filter((e) => e.event_type === "promotion").length;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <StatCard
        icon={<Dna className="w-5 h-5 text-purple-400" />}
        label="Total Evolutions"
        value={evolutionCount}
        color="purple"
      />
      <StatCard
        icon={<GitMerge className="w-5 h-5 text-blue-400" />}
        label="Merge Events"
        value={mergeCount}
        color="blue"
      />
      <StatCard
        icon={<Scissors className="w-5 h-5 text-amber-400" />}
        label="Prune Events"
        value={pruneCount}
        color="amber"
      />
      <StatCard
        icon={<TrendingUp className="w-5 h-5 text-emerald-400" />}
        label="Promotions"
        value={promotionCount}
        color="emerald"
      />
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: "purple" | "blue" | "amber" | "emerald";
}) {
  const borderColors = {
    purple: "border-purple-400/10",
    blue: "border-blue-400/10",
    amber: "border-amber-400/10",
    emerald: "border-emerald-400/10",
  };

  const bgColors = {
    purple: "bg-purple-500/10",
    blue: "bg-blue-500/10",
    amber: "bg-amber-500/10",
    emerald: "bg-emerald-500/10",
  };

  const textColors = {
    purple: "text-purple-300",
    blue: "text-blue-300",
    amber: "text-amber-300",
    emerald: "text-emerald-300",
  };

  return (
    <GlowCard className={borderColors[color]}>
      <div className="flex items-center gap-3">
        <div className={`p-2 ${bgColors[color]} rounded-xl`}>{icon}</div>
        <div>
          <div className="text-[11px] uppercase tracking-widest text-slate-400 font-semibold">
            {label}
          </div>
          <div className={`text-2xl font-bold ${textColors[color]}`}>{value}</div>
        </div>
      </div>
    </GlowCard>
  );
}
