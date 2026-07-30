"use client";

import React, { useState } from "react";
import {
  CreditCard,
  Zap,
  BarChart3,
  Calendar,
  ShieldCheck,
  ArrowUpRight,
  Download,
  Check,
  Layers,
  Network,
  Database,
  Infinity,
  HelpCircle,
  FileText,
  Clock,
  History
} from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

// --- Configuration ---

const SUBSCRIPTION_TIERS = [
  {
    id: "explorer",
    name: "Explorer",
    price: "$0",
    description: "Ideal for individuals starting their cognitive mapping journey.",
    features: [
      "1,000 Cognitive Nodes",
      "1-Hop Reasoning Depth",
      "Standard 3D Globe View",
      "Basic Semantic Search",
      "Daily Persistence Sync",
      "Community Support",
    ],
    buttonText: "Current Plan",
    active: true,
    highlight: false,
    color: "text-slate-400",
    bg: "bg-slate-500/5",
    border: "border-slate-500/20",
  },
  {
    id: "architect",
    name: "Architect",
    price: "$29",
    description: "For professionals building complex knowledge structures.",
    features: [
      "10,000 Cognitive Nodes",
      "4-Hop Reasoning Depth",
      "Full Semantic Alias Engine",
      "Graph Snapshots & Rollback",
      "Priority Graph Synthesis",
      "No Rate Limits",
    ],
    buttonText: "Upgrade to Pro",
    active: false,
    highlight: true,
    color: "text-indigo-400",
    bg: "bg-indigo-500/5",
    border: "border-indigo-500/30",
  },
  {
    id: "neural",
    name: "Neural",
    price: "$99",
    description: "Deep-scale reasoning for researchers and advanced teams.",
    features: [
      "100,000 Cognitive Nodes",
      "24-Hop Reasoning Depth",
      "Cross-Graph Reasoning",
      "Real-time Graph Evolution",
      "API Mastery (1M tokens/mo)",
      "Telemetry & Metric Export",
    ],
    buttonText: "Go Neural",
    active: false,
    highlight: false,
    color: "text-cyan-400",
    bg: "bg-cyan-500/5",
    border: "border-cyan-500/30",
  },
  {
    id: "matrix",
    name: "Matrix",
    price: "Custom",
    description: "The ultimate cognitive infrastructure for enterprise scale.",
    features: [
      "Unlimited Cognitive Nodes",
      "Infinite Reasoning Depth",
      "Private Memory Shards",
      "Dedicated Reasoning Worker",
      "Custom Domain Ontology",
      "24/7 Priority SLA",
    ],
    buttonText: "Contact Sales",
    active: false,
    highlight: false,
    color: "text-emerald-400",
    bg: "bg-emerald-500/5",
    border: "border-emerald-500/30",
  },
];

const INVOICE_HISTORY = [
  { id: "INV-2026-004", date: "May 01, 2026", amount: "$29.00", status: "Paid", type: "Subscription" },
  { id: "INV-2026-003", date: "Apr 01, 2026", amount: "$29.00", status: "Paid", type: "Subscription" },
  { id: "INV-2026-002", date: "Mar 15, 2026", amount: "$14.50", status: "Paid", type: "Credit Backfill" },
  { id: "INV-2026-001", date: "Mar 01, 2026", amount: "$29.00", status: "Paid", type: "Subscription" },
];

export default function BillingPage() {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");

  return (
    <div className="relative space-y-6 pb-12 text-slate-100 px-4 max-w-7xl mx-auto">
      <div className="faim-grid opacity-20" />

      <GlassHeader
        title="FAIM Matrix Billing"
        subtitle="Scale your cognitive capacity and manage your neural infrastructure"
        icon={CreditCard}
        actions={
          <div className="flex items-center gap-4 bg-black/20 p-1 rounded-lg border border-white/5">
            <button
              onClick={() => setBillingCycle("monthly")}
              className={`px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded-md transition-all ${
                billingCycle === "monthly" ? "bg-indigo-600 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle("yearly")}
              className={`px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded-md transition-all ${
                billingCycle === "yearly" ? "bg-indigo-600 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              Yearly <span className="text-[9px] text-emerald-400">(-20%)</span>
            </button>
          </div>
        }
      />

      {/* --- Usage Matrix Strip --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Node Capacity", value: "842 / 1,000", percent: 84.2, icon: Database, color: "bg-indigo-500" },
          { label: "Reasoning Credits", value: "12,450", sub: "Unlimited for Pro", icon: Network, color: "bg-cyan-500" },
          { label: "Graph Snapshots", value: "3 / 5", percent: 60, icon: Layers, color: "bg-amber-500" },
          { label: "Current Tier", value: "Explorer", sub: "Next bill June 01", icon: ShieldCheck, color: "bg-emerald-500" },
        ].map((stat) => (
          <div key={stat.label} className="p-4 rounded-xl border bg-slate-900/40 border-white/5 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] font-bold uppercase tracking-tighter text-slate-500">{stat.label}</p>
              <stat.icon size={14} className="text-slate-600" />
            </div>
            <p className="text-xl font-bold text-white mb-2">{stat.value}</p>
            {stat.percent !== undefined ? (
              <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full transition-all duration-1000" style={{ width: `${stat.percent}%`, backgroundColor: "var(--indigo-500)" }} />
              </div>
            ) : (
              <p className="text-[10px] text-slate-500 font-medium">{stat.sub}</p>
            )}
          </div>
        ))}
      </div>

      {/* --- Subscription Matrix --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {SUBSCRIPTION_TIERS.map((tier) => (
          <div
            key={tier.id}
            className={`relative flex flex-col p-6 rounded-2xl border transition-all duration-300 hover:translate-y-[-4px] ${
              tier.highlight ? "ring-2 ring-indigo-500/50 shadow-2xl shadow-indigo-500/10" : ""
            } ${tier.bg} ${tier.border}`}
          >
            {tier.highlight && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <Badge className="bg-indigo-600 text-white border-indigo-400">Most Popular</Badge>
              </div>
            )}
            
            <div className="mb-6">
              <h3 className="text-xl font-black text-white uppercase tracking-tight">{tier.name}</h3>
              <p className="text-xs text-slate-500 mt-1 h-8 leading-tight">{tier.description}</p>
            </div>

            <div className="mb-8">
              <p className="text-4xl font-black text-white">
                {tier.price}
                {tier.price !== "Custom" && (
                  <span className="text-sm font-normal text-slate-500 ml-1">
                    {billingCycle === "monthly" ? "/ mo" : "/ yr"}
                  </span>
                )}
              </p>
            </div>

            <div className="flex-grow space-y-4 mb-8">
              {tier.features.map((feature, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="mt-1 flex-shrink-0 w-4 h-4 rounded-full bg-emerald-500/10 flex items-center justify-center">
                    <Check size={10} className="text-emerald-400" />
                  </div>
                  <span className="text-xs text-slate-300 leading-none">{feature}</span>
                </div>
              ))}
            </div>

            <Button
              className={`w-full py-6 font-bold uppercase tracking-widest text-[10px] ${
                tier.active
                  ? "bg-transparent border border-white/10 text-slate-500 cursor-default hover:bg-transparent"
                  : tier.highlight
                  ? "bg-indigo-600 hover:bg-indigo-500 text-white"
                  : "bg-white/5 hover:bg-white/10 text-white"
              }`}
            >
              {tier.buttonText}
            </Button>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 pt-6">
        {/* Invoice History */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2">
              <History size={18} className="text-indigo-400" />
              <h2 className="text-lg font-bold text-white tracking-tight">Invoice History</h2>
            </div>
            <Button variant="ghost" size="sm" className="text-[10px] uppercase tracking-widest text-slate-500">
              Download All (PDF)
            </Button>
          </div>

          <div className="rounded-xl border border-white/5 bg-slate-900/40 overflow-hidden backdrop-blur-md">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 border-b border-white/5">
                <tr>
                  <th className="px-6 py-4 font-bold text-slate-500 uppercase tracking-widest">Invoice ID</th>
                  <th className="px-6 py-4 font-bold text-slate-500 uppercase tracking-widest">Date</th>
                  <th className="px-6 py-4 font-bold text-slate-500 uppercase tracking-widest">Type</th>
                  <th className="px-6 py-4 font-bold text-slate-500 uppercase tracking-widest text-right">Amount</th>
                  <th className="px-6 py-4 font-bold text-slate-500 uppercase tracking-widest text-center">Status</th>
                  <th className="px-6 py-4 font-bold text-slate-500 uppercase tracking-widest text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {INVOICE_HISTORY.map((inv) => (
                  <tr key={inv.id} className="group hover:bg-white/5 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-slate-300">{inv.id}</td>
                    <td className="px-6 py-4 text-slate-400">{inv.date}</td>
                    <td className="px-6 py-4">
                      <Badge variant="outline" size="xs" className="opacity-60">{inv.type}</Badge>
                    </td>
                    <td className="px-6 py-4 font-bold text-white text-right tabular-nums">{inv.amount}</td>
                    <td className="px-6 py-4 text-center">
                      <span className="text-[9px] font-black uppercase bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded">
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-2 rounded-lg hover:bg-white/10 transition-colors text-slate-500 hover:text-white">
                        <Download size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Why FAIM? */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-2">
            <HelpCircle size={18} className="text-amber-400" />
            <h2 className="text-lg font-bold text-white tracking-tight">Why pay for FAIM?</h2>
          </div>
          <div className="p-6 rounded-2xl border border-amber-500/20 bg-amber-500/5 space-y-6">
            <div className="space-y-2">
              <h4 className="text-xs font-black uppercase text-amber-400 tracking-widest">Deterministic Reasoning</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Unlike standard LLMs, FAIM is a structural knowledge engine. Your graphs never hallucinate relationships; they represent cold, hard semantic logic that scales with your depth.
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="text-xs font-black uppercase text-amber-400 tracking-widest">Infinite Memory Persistence</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Standard memory systems are transient. FAIM's cognitive atoms are persistent across sessions, building a "Second Brain" that grows smarter as your tiers increase.
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="text-xs font-black uppercase text-amber-400 tracking-widest">Neural Infrastructure</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Paying for FAIM supports the massive GPU/CPU resources required for fractal graph evolution and multi-hop semantic synthesis.
              </p>
            </div>
            <Button className="w-full bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 py-6 text-[10px] uppercase tracking-[0.2em] font-black">
              View Detailed FAQ
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
