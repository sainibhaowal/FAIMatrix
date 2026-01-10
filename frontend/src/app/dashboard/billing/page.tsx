"use client";

import React, { useEffect, useState } from "react";
import {
  Check,
  ArrowRight,
  Star,
  Zap,
  Crown,
  Sparkles,
  Loader2,
  RefreshCw,
  HardDrive,
} from "lucide-react";
import { getSession } from "next-auth/react";

interface UsageData {
  plan: string;
  tokens_used: number;
  tokens_max: number;
  storage_used_bytes: number;
  storage_max_bytes: number;
}

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    tokens: "1M",
    tokensNum: 1_000_000,
    storage: "100MB",
    storageMb: 100,
    features: [
      "1M Token Storage",
      "100MB Storage",
      "1 API Key",
      "Community Support",
    ],
    color: "cyan",
    icon: Zap,
    popular: false,
  },
  {
    id: "starter",
    name: "Starter",
    price: 9,
    tokens: "3M",
    tokensNum: 3_000_000,
    storage: "500MB",
    storageMb: 500,
    features: [
      "3M Token Storage",
      "500MB Storage",
      "Unlimited API Keys",
      "Priority Support",
    ],
    color: "purple",
    icon: Star,
    popular: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: 15,
    tokens: "10M",
    tokensNum: 10_000_000,
    storage: "2GB",
    storageMb: 2000,
    features: [
      "10M Token Storage",
      "2GB Storage",
      "Unlimited API Keys",
      "Priority Support",
      "Advanced Search",
      "Export Data",
    ],
    color: "amber",
    icon: Crown,
    popular: false,
  },
];

const COLOR_CLASSES = {
  cyan: {
    bg: "bg-cyan-500/20",
    bgActive: "bg-cyan-900/20",
    border: "border-cyan-500/50",
    ring: "ring-cyan-500/30",
    text: "text-cyan-400",
    token: "bg-cyan-500/10 border-cyan-500/20",
    btn: "bg-cyan-500 hover:bg-cyan-400",
  },
  purple: {
    bg: "bg-purple-500/20",
    bgActive: "bg-purple-900/20",
    border: "border-purple-500/50",
    ring: "ring-purple-500/30",
    text: "text-purple-400",
    token: "bg-purple-500/10 border-purple-500/20",
    btn: "bg-purple-500 hover:bg-purple-400",
  },
  amber: {
    bg: "bg-amber-500/20",
    bgActive: "bg-amber-900/20",
    border: "border-amber-500/50",
    ring: "ring-amber-500/30",
    text: "text-amber-400",
    token: "bg-amber-500/10 border-amber-500/20",
    btn: "bg-amber-500 hover:bg-amber-400",
  },
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export default function BillingPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchUsage = async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      // Get real billing status with usage data
      const resBilling = await fetch("/api/billing/status", { headers });
      if (!resBilling.ok) throw new Error("Failed to load billing data");
      
      const billingData = await resBilling.json();

      setUsage({
        plan: billingData.plan || "free",
        tokens_used: billingData.tokens_used || 0,
        tokens_max: billingData.tokens_max || 1_000_000,
        storage_used_bytes: billingData.storage_used_bytes || 0,
        storage_max_bytes: billingData.storage_max_bytes || 104_857_600,
      });
      setError(null);
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Failed to load billing info");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchUsage();
  }, []);

  const handleUpgrade = async (planId: string) => {
    if (planId === "free" || planId === usage?.plan) return;

    setUpgrading(planId);
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch("/api/billing/upgrade", {
        method: "POST",
        headers,
        body: JSON.stringify({ plan: planId }),
      });

      const data = await res.json();

      if (res.ok) {
        // Refresh usage data
        await fetchUsage();
        alert(`Successfully upgraded to ${planId}!`);
      } else {
        alert(data.detail || "Upgrade failed");
      }
    } catch (err: any) {
      alert(err.message || "Error upgrading plan");
    } finally {
      setUpgrading(null);
    }
  };

  const currentPlan = usage?.plan || "free";
  const tokensUsedPercent = usage
    ? Math.min(100, (usage.tokens_used / usage.tokens_max) * 100)
    : 0;
  const storageUsedPercent = usage
    ? Math.min(100, (usage.storage_used_bytes / usage.storage_max_bytes) * 100)
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-cyan-400" size={24} />
        <span className="ml-2 text-slate-400">Loading billing info...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <header className="text-center">
        <h1 className="text-xl font-bold text-slate-100 flex items-center justify-center gap-2">
          <Sparkles className="text-purple-400" size={20} />
          FAIM Lab Plans
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Simple, transparent pricing. Pay for what you need.
        </p>
      </header>

      {/* Current Usage Card */}
      {usage && (
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
              onClick={() => fetchUsage(true)}
              disabled={refreshing}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-all"
              title="Refresh usage"
            >
              <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Token Usage Bar */}
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

            {/* Storage Usage Bar */}
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
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-900/30 border border-red-500/50 rounded-xl p-4 text-center text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Plan Cards */}
      <div className="grid md:grid-cols-3 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = currentPlan === plan.id;
          const isUpgrade =
            PLANS.findIndex((p) => p.id === currentPlan) <
            PLANS.findIndex((p) => p.id === plan.id);
          const Icon = plan.icon;

          const colors =
            COLOR_CLASSES[plan.color as keyof typeof COLOR_CLASSES];

          return (
            <div
              key={plan.id}
              className={`relative p-5 rounded-2xl border transition-all ${
                isCurrent
                  ? `${colors.bgActive} ${colors.border} ring-2 ${colors.ring}`
                  : plan.popular
                    ? "bg-gradient-to-b from-purple-900/30 to-slate-900/40 border-purple-500/40 hover:border-purple-400/60"
                    : "bg-slate-900/40 border-slate-700/50 hover:border-slate-600/50"
              }`}
            >
              {/* Popular Badge */}
              {plan.popular && !isCurrent && (
                <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-purple-500 text-white text-[10px] font-bold rounded-full">
                  MOST POPULAR
                </div>
              )}

              {/* Current Badge */}
              {isCurrent && (
                <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-cyan-500 text-white text-[10px] font-bold rounded-full">
                  CURRENT PLAN
                </div>
              )}

              {/* Plan Icon & Name */}
              <div className="flex items-center gap-2 mb-3">
                <div className={`p-2 rounded-lg ${colors.bg}`}>
                  <Icon size={16} className={colors.text} />
                </div>
                <span className="text-sm font-semibold text-slate-200">
                  {plan.name}
                </span>
              </div>

              {/* Price */}
              <div className="mb-4">
                <span className="text-3xl font-bold text-white">
                  {plan.price === 0 ? "Free" : `$${plan.price}`}
                </span>
                {plan.price > 0 && (
                  <span className="text-sm text-slate-500">/month</span>
                )}
              </div>

              {/* Token Highlight */}
              <div className={`mb-4 py-2 px-3 rounded-lg ${colors.token}`}>
                <span className={`text-lg font-bold ${colors.text}`}>
                  {plan.tokens}
                </span>
                <span className="text-sm text-slate-400 ml-1">tokens</span>
              </div>

              {/* Features */}
              <ul className="space-y-2 mb-5">
                {plan.features.map((feature, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-2 text-xs text-slate-300"
                  >
                    <Check
                      size={12}
                      className={`${colors.text} flex-shrink-0`}
                    />
                    {feature}
                  </li>
                ))}
              </ul>

              {/* Action Button */}
              {isCurrent ? (
                <div className="py-2 px-4 rounded-lg bg-slate-700/50 text-slate-400 text-xs text-center">
                  Current Plan
                </div>
              ) : isUpgrade ? (
                <button
                  onClick={() => handleUpgrade(plan.id)}
                  disabled={upgrading !== null}
                  className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm transition-all flex items-center justify-center gap-2 ${
                    plan.popular
                      ? "bg-white text-black hover:bg-white/90"
                      : `${colors.btn} text-white`
                  }`}
                >
                  {upgrading === plan.id ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Upgrading...
                    </>
                  ) : (
                    <>
                      Upgrade to {plan.name}
                      <ArrowRight size={14} />
                    </>
                  )}
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade(plan.id)}
                  disabled={upgrading !== null}
                  className="w-full py-2 px-4 rounded-lg bg-slate-700/30 hover:bg-slate-700/50 text-slate-400 hover:text-slate-300 text-xs text-center transition-all"
                >
                  {upgrading === plan.id ? "Downgrading..." : "Downgrade"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* FAQ / Info */}
      <div className="text-center pt-4 border-t border-slate-800">
        <p className="text-xs text-slate-500">
          All plans include your permanent Universe ID and API access.
          <br />
          Usage is tracked in real-time across all memory operations.
        </p>
      </div>
    </div>
  );
}
