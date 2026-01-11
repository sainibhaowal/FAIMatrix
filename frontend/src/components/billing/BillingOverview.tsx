"use client";

import React from "react";
import { Zap, HardDrive, RefreshCw } from "lucide-react";

interface UsageData {
  plan: string;
  tokens_used: number;
  tokens_max: number;
  storage_used_bytes: number;
  storage_max_bytes: number;
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

  return (
    <div className="bg-slate-900/60 border border-slate-700/50 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-xs text-slate-500 uppercase tracking-wider">
            Current Plan
          </span>
          <div className="text-lg font-bold text-slate-100 capitalize">
            {currentPlan}
          </div>
        </div>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-all"
          title="Refresh usage"
        >
          <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="space-y-4">
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-slate-400">
            <span className="flex items-center gap-2">
              <Zap size={12} className="text-cyan-400" />
              Token Usage
            </span>
            <span className="font-mono">
              {(usage.tokens_used / 1_000_000).toFixed(2)}M /{" "}
              {(usage.tokens_max / 1_000_000).toFixed(0)}M
            </span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                tokensUsedPercent > 90
                  ? "bg-red-500"
                  : tokensUsedPercent > 70
                    ? "bg-yellow-500"
                    : "bg-gradient-to-r from-cyan-500 to-purple-500"
              }`}
              style={{ width: `${tokensUsedPercent}%` }}
            />
          </div>
          {tokensUsedPercent > 80 && (
            <p className="text-xs text-yellow-400">
              ⚠️ Running low on tokens. Consider upgrading!
            </p>
          )}
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs text-slate-400">
            <span className="flex items-center gap-2">
              <HardDrive size={12} className="text-purple-400" />
              Storage Usage
            </span>
            <span className="font-mono">
              {formatBytes(usage.storage_used_bytes)} /{" "}
              {formatBytes(usage.storage_max_bytes)}
            </span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                storageUsedPercent > 90
                  ? "bg-red-500"
                  : storageUsedPercent > 70
                    ? "bg-yellow-500"
                    : "bg-gradient-to-r from-purple-500 to-pink-500"
              }`}
              style={{ width: `${storageUsedPercent}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
