"use client";

import React from "react";
import { Check, ArrowRight, Star, Zap, Crown, Loader2 } from "lucide-react";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    tokens: "1M",
    features: ["1M Token Storage", "100MB Storage", "1 API Key", "Community Support"],
    color: "cyan",
    icon: Zap,
    popular: false,
  },
  {
    id: "starter",
    name: "Starter",
    price: 9,
    tokens: "3M",
    features: ["3M Token Storage", "500MB Storage", "Unlimited API Keys", "Priority Support"],
    color: "purple",
    icon: Star,
    popular: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: 15,
    tokens: "10M",
    features: ["10M Token Storage", "2GB Storage", "Unlimited API Keys", "Priority Support", "Advanced Search", "Export Data"],
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

interface PricingTiersProps {
  currentPlan: string;
  upgrading: string | null;
  onUpgrade: (planId: string) => void;
}

export function PricingTiers({ currentPlan, upgrading, onUpgrade }: PricingTiersProps) {
  return (
    <div className="grid md:grid-cols-3 gap-4">
      {PLANS.map((plan) => {
        const isCurrent = currentPlan === plan.id;
        const isUpgrade =
          PLANS.findIndex((p) => p.id === currentPlan) <
          PLANS.findIndex((p) => p.id === plan.id);
        const Icon = plan.icon;
        const colors = COLOR_CLASSES[plan.color as keyof typeof COLOR_CLASSES];

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
            {plan.popular && !isCurrent && (
              <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-purple-500 text-white text-[10px] font-bold rounded-full">
                MOST POPULAR
              </div>
            )}
            {isCurrent && (
              <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-cyan-500 text-white text-[10px] font-bold rounded-full">
                CURRENT PLAN
              </div>
            )}

            <div className="flex items-center gap-2 mb-3">
              <div className={`p-2 rounded-lg ${colors.bg}`}>
                <Icon size={16} className={colors.text} />
              </div>
              <span className="text-sm font-semibold text-slate-200">
                {plan.name}
              </span>
            </div>

            <div className="mb-4">
              <span className="text-3xl font-bold text-white">
                {plan.price === 0 ? "Free" : `$${plan.price}`}
              </span>
              {plan.price > 0 && (
                <span className="text-sm text-slate-500">/month</span>
              )}
            </div>

            <div className={`mb-4 py-2 px-3 rounded-lg ${colors.token}`}>
              <span className={`text-lg font-bold ${colors.text}`}>
                {plan.tokens}
              </span>
              <span className="text-sm text-slate-400 ml-1">tokens</span>
            </div>

            <ul className="space-y-2 mb-5">
              {plan.features.map((feature, i) => (
                <li key={i} className="flex items-center gap-2 text-xs text-slate-300">
                  <Check size={12} className={`${colors.text} flex-shrink-0`} />
                  {feature}
                </li>
              ))}
            </ul>

            {isCurrent ? (
              <div className="py-2 px-4 rounded-lg bg-slate-700/50 text-slate-400 text-xs text-center">
                Current Plan
              </div>
            ) : isUpgrade ? (
              <button
                onClick={() => onUpgrade(plan.id)}
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
                onClick={() => onUpgrade(plan.id)}
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
  );
}
