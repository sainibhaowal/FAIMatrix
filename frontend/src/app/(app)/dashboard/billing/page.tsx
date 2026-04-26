"use client";

import React from "react";
import {
  CreditCard,
  Zap,
  BarChart3,
  Calendar,
  ShieldCheck,
  ArrowUpRight,
  Download,
} from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export default function BillingPage() {
  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader
        title="Resource Subscriptions"
        subtitle="Manage compute allocations, credit balances, and usage billing"
        icon={CreditCard}
        actions={
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              size="md"
              className="border-emerald-500/30 text-emerald-400 bg-emerald-500/5"
            >
              Premium Tier
            </Badge>
            <Button size="sm" variant="outline">
              Update Plan
            </Button>
          </div>
        }
      />

      {/* --- Billing Metric Strip --- */}
      <div
        className="grid grid-cols-1 overflow-hidden rounded-xl border sm:grid-cols-2 xl:grid-cols-4"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        {[
          {
            label: "Current Spend",
            value: "$142.80",
            sub: "Month to date",
            icon: <CreditCard size={18} />,
            color: "text-emerald-400",
          },
          {
            label: "Available Credits",
            value: "840",
            sub: "Expires in 12 days",
            icon: <Zap size={18} />,
            color: "text-cyan-200",
          },
          {
            label: "Next Invoice",
            value: "May 01",
            sub: "Auto-pay enabled",
            icon: <Calendar size={18} />,
            color: "text-amber-400",
          },
          {
            label: "Compute Usage",
            value: "82.4%",
            sub: "Higher than average",
            icon: <BarChart3 size={18} />,
            color: "text-rose-400",
          },
        ].map((stat, i) => (
          <div
            key={stat.label}
            className="relative flex flex-col justify-center px-6 py-3"
            style={{
              borderLeft: i > 0 ? "1px solid var(--os-stroke)" : undefined,
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                {stat.label}
              </p>
              <div className="opacity-20">{stat.icon}</div>
            </div>
            <p
              className="font-semibold tabular-nums leading-none"
              style={{ fontSize: 26 }}
            >
              <span className={stat.color}>{stat.value}</span>
            </p>
            <p className="mt-2 text-[10px] text-slate-500 font-bold uppercase tracking-widest">
              {stat.sub}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Subscription Tier Panel */}
        <div
          className="lg:col-span-2 overflow-hidden rounded-xl border flex flex-col"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <div
            className="border-b px-5 py-1.5"
            style={{ borderColor: "var(--os-stroke)" }}
          >
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
              Subscription Matrix
            </p>
          </div>

          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              className="p-6 rounded-xl border flex flex-col justify-between h-full bg-indigo-500/5"
              style={{ borderColor: "rgba(99,102,241,0.2)" }}
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <Badge variant="success" size="xs">
                    Active
                  </Badge>
                  <ShieldCheck size={20} className="text-indigo-400" />
                </div>
                <h3 className="text-xl font-bold text-white">Neural Premium</h3>
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                  Full access to fractal evolution engines, unlimited API keys,
                  and priority telemetry throughput.
                </p>
              </div>
              <div className="mt-8 pt-6 border-t border-indigo-500/10">
                <p className="text-2xl font-bold text-white">
                  $49
                  <span className="text-sm font-normal text-slate-500">
                    {" "}
                    / month
                  </span>
                </p>
              </div>
            </div>

            <div
              className="p-6 rounded-xl border flex flex-col justify-between h-full hover:bg-white/5 transition-all cursor-pointer group"
              style={{
                borderColor: "var(--os-stroke)",
                background: "var(--os-surface-2)",
              }}
            >
              <div>
                <div className="flex items-center justify-between mb-4 opacity-40">
                  <Badge variant="outline" size="xs">
                    Available
                  </Badge>
                  <ArrowUpRight
                    size={20}
                    className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform"
                  />
                </div>
                <h3 className="text-xl font-bold text-slate-300">
                  Enterprise Core
                </h3>
                <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                  Isolated neural environments, custom data sovereignty rules,
                  and dedicated hardware allocation.
                </p>
              </div>
              <div className="mt-8 pt-6 border-t border-white/5">
                <p className="text-sm font-bold text-slate-400">
                  Custom Volume Pricing
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Invoice Summary */}
        <div
          className="overflow-hidden rounded-xl border flex flex-col"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <div
            className="border-b px-5 py-3 flex items-center justify-between"
            style={{ borderColor: "var(--os-stroke)" }}
          >
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
              Recent Invoices
            </p>
            <Button
              variant="ghost"
              className="h-6 px-2 text-[9px] uppercase tracking-widest"
            >
              History
            </Button>
          </div>

          <div className="p-4 space-y-2 overflow-y-auto max-h-[320px] custom-scrollbar">
            {[
              {
                id: "INV-8211",
                amt: "$49.00",
                date: "Apr 01, 2026",
                status: "Paid",
              },
              {
                id: "INV-7944",
                amt: "$49.00",
                date: "Mar 01, 2026",
                status: "Paid",
              },
              {
                id: "INV-7622",
                amt: "$12.40",
                date: "Feb 14, 2026",
                status: "Credit",
              },
              {
                id: "INV-7109",
                amt: "$49.00",
                date: "Feb 01, 2026",
                status: "Paid",
              },
            ].map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between p-3 rounded-lg border group transition-all hover:bg-[var(--glass-hover)]"
                style={{
                  background: "var(--os-surface-2)",
                  borderColor: "var(--os-stroke)",
                }}
              >
                <div className="space-y-1">
                  <p className="text-[11px] font-bold text-slate-100">
                    {inv.id}
                  </p>
                  <p className="text-[10px] text-slate-500">{inv.date}</p>
                </div>
                <div className="text-right space-y-1">
                  <p className="text-[11px] font-bold text-slate-100">
                    {inv.amt}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] uppercase tracking-widest text-emerald-400 font-black">
                      {inv.status}
                    </span>
                    <Download
                      size={10}
                      className="text-slate-500 group-hover:text-slate-200 transition-colors cursor-pointer"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
