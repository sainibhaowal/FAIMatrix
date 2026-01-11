"use client";

import React, { useEffect, useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { getSession } from "next-auth/react";
import { BillingOverview, PricingTiers } from "@/components";

interface UsageData {
  plan: string;
  tokens_used: number;
  tokens_max: number;
  storage_used_bytes: number;
  storage_max_bytes: number;
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
        <BillingOverview 
          usage={usage} 
          refreshing={refreshing} 
          onRefresh={() => fetchUsage(true)} 
        />
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-900/30 border border-red-500/50 rounded-xl p-4 text-center text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Plan Cards */}
      <PricingTiers 
        currentPlan={usage?.plan || "free"} 
        upgrading={upgrading} 
        onUpgrade={handleUpgrade} 
      />

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
