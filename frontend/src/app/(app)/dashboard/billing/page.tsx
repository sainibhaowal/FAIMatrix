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
  api_calls_count?: number;
  api_calls_max?: number;
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
        tokens_used: billingData.memories_count || 0,
        tokens_max: billingData.memories_max || 1_000_000,
        storage_used_bytes: billingData.storage_used_bytes || 0,
        storage_max_bytes: billingData.storage_max_bytes || 104_857_600,
        api_calls_count: billingData.api_calls_count || 0,
        api_calls_max: billingData.api_calls_max || 10000,
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
      <section className="pt-12 border-t border-white/5">
        <h2 className="text-lg font-black text-white text-center mb-8 italic">Feature Comparison</h2>
        <div className="bg-white/[0.02] border border-white/5 rounded-[2rem] overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.02]">
                <th className="px-6 py-4 font-black text-slate-500 uppercase tracking-widest">Feature</th>
                <th className="px-6 py-4 font-black text-slate-500 uppercase tracking-widest">Free</th>
                <th className="px-6 py-4 font-black text-cyan-400 uppercase tracking-widest">Starter</th>
                <th className="px-6 py-4 font-black text-purple-400 uppercase tracking-widest">Pro</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {[
                ["Neural Token Storage", "1M", "3M", "10M"],
                ["Fractal Storage Scale", "100MB", "500MB", "2GB"],
                ["API Key Concurrency", "1 Key", "Unlimited", "Unlimited"],
                ["Retrieval Precision", "Standard", "Enhanced", "Neural Boosted"],
                ["Knowledge Regions", "10", "Unlimited", "Unlimited"],
                ["Export & Takeout", "—", "—", "Full JSON/PDF"],
              ].map(([name, free, starter, pro], i) => (
                <tr key={i} className="hover:bg-white/[0.01] transition-colors">
                  <td className="px-6 py-4 font-bold text-slate-300">{name}</td>
                  <td className="px-6 py-4 text-slate-500">{free}</td>
                  <td className="px-6 py-4 text-slate-400">{starter}</td>
                  <td className="px-6 py-4 text-slate-100 font-bold">{pro}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="text-center pt-8">
        <p className="text-[10px] text-slate-600 font-black uppercase tracking-widest leading-relaxed">
          Proprietary Fractal AI Memory Engine (FAIM) — All Rights Reserved.
          <br />
          Usage metrics are audited in real-time across the Global Synaptic Network.
        </p>
      </div>
    </div>
  );
}
