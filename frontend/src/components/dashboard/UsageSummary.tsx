"use client";

import React from "react";
import Link from "next/link";
import { Zap, ArrowRight } from "lucide-react";
import { Card, Progress } from "@/components/ui";

interface UsageSummaryProps {
  used: number;
  limit: number;
  percent: number;
}

export function UsageSummary({ used, limit, percent }: UsageSummaryProps) {
  const isWarning = percent >= 80;

  return (
    <div className="space-y-4">
      {/* Upgrade CTA Banner - Shows when usage > 80% */}
      {isWarning && (
        <div className="relative overflow-hidden rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-amber-400/5 to-orange-500/10 p-4">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_left,rgba(251,191,36,0.1),transparent_50%)]" />
          <div className="relative flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20">
                <Zap size={20} className="text-amber-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-amber-200">
                  {percent >= 100 ? "Token Limit Reached!" : "Approaching Token Limit"}
                </h3>
                <p className="text-xs text-amber-300/70">
                  {percent >= 100 
                    ? "Upgrade to continue using FAIM without interruption." 
                    : `You've used ${percent}% of your token quota. Consider upgrading for more capacity.`}
                </p>
              </div>
            </div>
            <Link
              href="/dashboard/billing"
              className="shrink-0 rounded-lg bg-amber-500 px-4 py-2 text-xs font-semibold text-slate-900 shadow-lg shadow-amber-500/25 hover:bg-amber-400 transition-colors"
            >
              Upgrade Now
            </Link>
          </div>
        </div>
      )}

      {/* Token Usage Bar - Always visible */}
      <Card className="!p-4" glow={!isWarning}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-[var(--text-secondary)]">Token Usage</span>
          <span className="text-sm font-medium text-[var(--text-primary)]">
            {(used / 1000).toFixed(0)}K / {(limit / 1000).toFixed(0)}K
          </span>
        </div>
        <Progress
          value={percent}
          variant={isWarning ? "warning" : "primary"}
          size="md"
          animated={isWarning}
        />
        {isWarning && (
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--border-subtle)]">
            <span className="text-xs text-[var(--faim-warning)]">
              You&apos;ve used {percent}% of your tokens
            </span>
            <Link
              href="/dashboard/billing"
              className="text-xs font-medium text-[var(--faim-primary)] hover:underline flex items-center gap-1"
            >
              Upgrade Plan <ArrowRight size={12} />
            </Link>
          </div>
        )}
      </Card>
    </div>
  );
}
