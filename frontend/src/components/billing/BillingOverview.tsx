"use client";

import React from "react";
import { Zap, HardDrive, RefreshCw } from "lucide-react";

interface UsageData {
  plan: string;
  tokens_used: number;
  tokens_max: number;
  storage_used_bytes: number;
  storage_max_bytes: number;
  api_calls_count?: number;
  api_calls_max?: number;
}

interface BillingOverviewProps {
  usage: UsageData;
  refreshing: boolean;
  onRefresh: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export function BillingOverview({ usage, refreshing, onRefresh }: BillingOverviewProps) {
  const currentPlan = usage.plan || "free";
  const tokensUsedPercent = Math.min(100, (usage.tokens_used / usage.tokens_max) * 100);
  const storageUsedPercent = Math.min(100, (usage.storage_used_bytes / usage.storage_max_bytes) * 100);
  const apiCallsCount = usage.api_calls_count || 0;
  const apiCallsMax = usage.api_calls_max || 10000;
  const apiCallsPercent = Math.min(100, (apiCallsCount / apiCallsMax) * 100);

  return (
    <div className="relative overflow-hidden group">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-emerald-500/10 rounded-3xl" />
      <div className="relative bg-[var(--surface-1)] border border-[var(--border-default)] rounded-3xl p-8 backdrop-blur-2xl shadow-2xl">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-cyan-500 to-purple-500 p-0.5 shadow-lg shadow-cyan-500/20">
              <div className="h-full w-full rounded-[14px] bg-slate-900 flex items-center justify-center">
                <Zap size={24} className="text-cyan-400" />
              </div>
            </div>
            <div>
              <div className="text-[10px] text-[var(--text-muted)] uppercase tracking-[0.3em] font-black">Industrial Lifecycle</div>
              <div className="text-3xl font-black text-[var(--text-primary)] tracking-tighter flex items-center gap-3">
                {currentPlan.toUpperCase()}
                <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-3 py-1 rounded-full border border-emerald-500/20 font-bold tracking-widest uppercase">Operational</span>
              </div>
            </div>
          </div>
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="group/refresh p-4 rounded-2xl bg-[var(--surface-2)] hover:bg-[var(--surface-3)] text-[var(--text-muted)] hover:text-indigo-400 transition-all border border-[var(--border-subtle)] shadow-lg"
            title="Calibrate Usage Telemetry"
          >
            <RefreshCw size={22} className={refreshing ? "animate-spin" : "group-hover/refresh:rotate-180 transition-transform duration-700"} />
          </button>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {/* Token Usage */}
          <div className="space-y-3">
            <div className="flex justify-between items-end">
              <div>
                <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Neural Tokens</div>
                <div className="text-lg font-bold text-white tracking-tight">
                  {(usage.tokens_used / 1_000).toFixed(1)}K <span className="text-slate-500 font-normal">/ {(usage.tokens_max / 1_000).toFixed(0)}K</span>
                </div>
              </div>
              <div className="text-[10px] font-bold text-cyan-400">
                {tokensUsedPercent.toFixed(1)}%
              </div>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden border border-white/[0.03]">
              <div
                className={`h-full transition-all duration-1000 ease-out relative ${
                  tokensUsedPercent > 90
                    ? "bg-rose-500"
                    : tokensUsedPercent > 70
                      ? "bg-amber-500"
                      : "bg-cyan-500"
                }`}
                style={{ width: `${tokensUsedPercent}%` }}
              >
                <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.2)_50%,transparent_100%)] animate-shimmer" />
              </div>
            </div>
          </div>

          {/* Storage Usage */}
          <div className="space-y-3">
            <div className="flex justify-between items-end">
              <div>
                <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Synaptic Storage</div>
                <div className="text-lg font-bold text-white tracking-tight">
                  {formatBytes(usage.storage_used_bytes)} <span className="text-slate-500 font-normal">/ {formatBytes(usage.storage_max_bytes)}</span>
                </div>
              </div>
              <div className="text-[10px] font-bold text-purple-400">
                {storageUsedPercent.toFixed(1)}%
              </div>
            </div>
            <div className="h-2 bg-[var(--surface-3)] rounded-full overflow-hidden border border-[var(--border-subtle)] shadow-inner">
              <div
                className={`h-full transition-all duration-1000 ease-out relative ${
                  storageUsedPercent > 90
                    ? "bg-rose-500"
                    : storageUsedPercent > 70
                      ? "bg-amber-500"
                      : "bg-indigo-500"
                }`}
                style={{ width: `${storageUsedPercent}%` }}
              >
                <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.3)_50%,transparent_100%)] animate-shimmer" />
              </div>
            </div>
          </div>

          {/* API Operations */}
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <div>
                <div className="text-[10px] text-[var(--text-muted)] uppercase font-black tracking-widest mb-1.5 opacity-60">Neural Operations</div>
                <div className="text-xl font-black text-[var(--text-primary)] tracking-tighter">
                  {(apiCallsCount / 1000).toFixed(1)}K <span className="text-[var(--text-muted)] font-bold opacity-40">/ {(apiCallsMax / 1000).toFixed(0)}K</span>
                </div>
              </div>
              <div className="text-[10px] font-black text-emerald-400 tabular-nums tracking-tighter">
                {apiCallsPercent.toFixed(1)}%
              </div>
            </div>
            <div className="h-2 bg-[var(--surface-3)] rounded-full overflow-hidden border border-[var(--border-subtle)] shadow-inner">
              <div
                className={`h-full transition-all duration-1000 ease-out relative ${
                  apiCallsPercent > 90
                    ? "bg-rose-500"
                    : apiCallsPercent > 70
                      ? "bg-amber-500"
                      : "bg-emerald-500"
                }`}
                style={{ width: `${apiCallsPercent}%` }}
              >
                <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent_0%,rgba(255,255,255,0.3)_50%,transparent_100%)] animate-shimmer" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
